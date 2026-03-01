from __future__ import annotations

import json
import logging
import signal
import subprocess
import uuid
from pathlib import Path

from .config import Config
from .extract.cobol_filter import is_cobol_file, has_multi_extension, is_binary_file, looks_like_cobol
from .extract.dialect import detect_dialect
from .extract.format_detector import detect_source_format
from .extract.hasher import sha256
from .extract.normalizer import normalize_cobol
from .state import StateManager
from .vcs.git_tools import mirror_clone

log = logging.getLogger(__name__)


class CorpusOrchestrator:

    def __init__(self, base_dir: Path, config: Config):
        self.base_dir = base_dir
        self.mirror_dir = base_dir / "mirrors"
        self.repos_dir = base_dir / "repos"
        self.working_dir = base_dir / "working"
        self.data_dir = base_dir / "data"

        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

        self.state = StateManager(self.data_dir)
        self.run_id = str(uuid.uuid4())
        self.state.create_run(self.run_id, json.dumps(vars(config), default=str))

        self._repos_processed = 0
        self._repos_failed = 0
        self._files_extracted = 0
        self._shutdown_requested = False

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def _handle_shutdown(self, signum: int, frame: object) -> None:
        log.warning("Shutdown requested (signal %d), finishing current repo...", signum)
        self._shutdown_requested = True

    def register_repo(self, repo_meta: dict) -> None:
        self.state.upsert_repo(repo_meta, self.run_id)

    def process_repo(self, repo_meta: dict) -> None:
        repo_id = repo_meta["id"]

        status = self.state.get_repo_status(repo_id)
        if status == "done":
            log.info("Skipping already completed repo: %s", repo_id)
            return

        try:
            self._do_process(repo_meta)
            self.state.set_repo_status(repo_id, "done")
            self._repos_processed += 1
        except Exception as exc:
            log.error("Failed processing %s: %s", repo_id, exc)
            self.state.set_repo_status(repo_id, "failed", str(exc))
            self._repos_failed += 1
        finally:
            self.state.flush()

    def _do_process(self, repo_meta: dict) -> None:
        repo_id = repo_meta["id"]

        self.state.set_repo_status(repo_id, "cloning")
        log.info("Cloning %s", repo_id)
        mirror_path = mirror_clone(
            repo_id,
            repo_meta["clone_url"],
            self.mirror_dir,
        )

        self.state.set_repo_status(repo_id, "cloned")

        if self.working_dir.exists():
            subprocess.run(["rm", "-rf", str(self.working_dir)], check=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        log.info("Checking out %s", repo_id)
        subprocess.run(
            [
                "git",
                "--git-dir", str(mirror_path),
                "--work-tree", str(self.working_dir),
                "checkout", "-f", "HEAD",
            ],
            check=True,
        )

        self.state.set_repo_status(repo_id, "extracting")
        repo_out_dir = self.repos_dir / repo_id
        extracted = 0

        for file in self.working_dir.rglob("*"):
            if not (file.is_file() and is_cobol_file(file)):
                continue
            if has_multi_extension(file):
                log.debug("Skipping multi-extension file: %s", file.name)
                continue
            if is_binary_file(file):
                log.debug("Skipping binary file: %s", file.name)
                continue

            content = file.read_text(errors="replace")
            if not looks_like_cobol(content):
                log.debug("Skipping non-COBOL content: %s", file.name)
                continue
            source_format = detect_source_format(content)
            normalized = normalize_cobol(content)
            file_hash = sha256(normalized)

            original_path = str(file.relative_to(self.working_dir))

            # Store file in original directory structure
            dest = repo_out_dir / original_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(normalized)

            store_path = f"{repo_id}/{original_path}"

            if not self.state.file_exists(file_hash):
                dialect_tags = detect_dialect(normalized)
                file_type = file.suffix.lower().lstrip(".")
                self.state.add_file(
                    file_hash=file_hash,
                    store_path=store_path,
                    byte_size=len(normalized.encode("utf-8")),
                    line_count=normalized.count("\n") + 1,
                    file_type=file_type,
                    dialect_tags=dialect_tags,
                    source_format=source_format,
                )
                self._files_extracted += 1

            self.state.add_provenance(file_hash, repo_id, self.run_id, original_path)
            extracted += 1

        log.info("Extracted %d COBOL files from %s", extracted, repo_id)

    def finish(self) -> None:
        self.state.finish_run(
            self.run_id,
            self._repos_processed,
            self._repos_failed,
            self._files_extracted,
        )
        self.state.flush()

        if self.working_dir.exists():
            subprocess.run(["rm", "-rf", str(self.working_dir)], check=True)

        log.info(
            "Run complete: %d processed, %d failed, %d new files",
            self._repos_processed,
            self._repos_failed,
            self._files_extracted,
        )

    def close(self) -> None:
        self.state.close()
