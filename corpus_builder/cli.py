from __future__ import annotations

import logging
import shutil
from pathlib import Path

import typer

from .config import load_config
from .evaluate import RepoMetadata, evaluate_repo
from .orchestrator import CorpusOrchestrator
from .sources.registry import get_adapter, list_adapters
from .state import StateManager

app = typer.Typer(
    name="corpus-builder",
    help="Build a deduplicated COBOL corpus from public repositories.",
)

log = logging.getLogger("corpus_builder")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@app.command()
def discover(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Discover repositories and populate the manifest without extracting."""
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)
    log.info("Starting discovery")
    log.info("Available adapters: %s", ", ".join(list_adapters()))

    base_dir = Path(cfg.output_dir)
    data_dir = base_dir / "data"
    state = StateManager(data_dir)

    new_count = 0
    total = 0
    try:
        for name, src_cfg in cfg.sources.items():
            if not src_cfg.enabled:
                log.info("Source disabled: %s", name)
                continue

            adapter = get_adapter(name, src_cfg)
            if adapter is None:
                continue

            max_label = str(src_cfg.max_repos) if src_cfg.max_repos else "unlimited"
            log.info(
                "Discovering repos from %s (query=%s, max=%s)",
                name,
                src_cfg.query,
                max_label,
            )

            for repo in adapter.discover_repositories():
                is_new = state.upsert_repo(repo, run_id=None)
                if is_new:
                    new_count += 1

        state.flush()
        total = state.con.execute("SELECT count(*) FROM repos").fetchone()[0]
    finally:
        state.close()

    log.info("Discovered %d new repos, %d total in manifest", new_count, total)


@app.command()
def extract(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Extract COBOL files from repos already in the manifest."""
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)
    log.info("Starting extraction from manifest")

    base_dir = Path(cfg.output_dir)
    orchestrator = CorpusOrchestrator(base_dir, cfg)

    try:
        incomplete = orchestrator.state.get_incomplete_repos()
        if not incomplete:
            log.info("No incomplete repos to extract")
        else:
            log.info("Extracting %d incomplete repos", len(incomplete))
            for repo in incomplete:
                if orchestrator.shutdown_requested:
                    break
                orchestrator.process_repo(repo)

        orchestrator.finish()
    finally:
        orchestrator.close()

    log.info("Extraction complete")


@app.command()
def run(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Run the full pipeline: discover repos then extract COBOL files."""
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)
    log.info("Starting corpus builder")
    log.info("Available adapters: %s", ", ".join(list_adapters()))

    base_dir = Path(cfg.output_dir)
    orchestrator = CorpusOrchestrator(base_dir, cfg)

    try:
        for name, src_cfg in cfg.sources.items():
            if not src_cfg.enabled:
                log.info("Source disabled: %s", name)
                continue

            adapter = get_adapter(name, src_cfg)
            if adapter is None:
                continue

            max_label = str(src_cfg.max_repos) if src_cfg.max_repos else "unlimited"
            log.info(
                "Discovering repos from %s (query=%s, max=%s)",
                name,
                src_cfg.query,
                max_label,
            )

            for repo in adapter.discover_repositories():
                if orchestrator.shutdown_requested:
                    log.info("Shutdown requested, stopping discovery")
                    break
                orchestrator.register_repo(repo)
                orchestrator.process_repo(repo)

            if orchestrator.shutdown_requested:
                break

        # Resume any incomplete repos from previous runs
        if not orchestrator.shutdown_requested:
            incomplete = orchestrator.state.get_incomplete_repos()
            if incomplete:
                log.info("Resuming %d incomplete repos from previous runs", len(incomplete))
                for repo in incomplete:
                    if orchestrator.shutdown_requested:
                        break
                    orchestrator.process_repo(repo)

        orchestrator.finish()
    finally:
        orchestrator.close()

    log.info("Pipeline complete")


def _remove_dir_and_prune_parents(path: Path, stop_at: Path) -> None:
    """Remove a directory tree, then prune empty parent dirs up to stop_at."""
    if path.exists():
        shutil.rmtree(path)
    parent = path.parent
    while parent != stop_at and parent.exists():
        try:
            parent.rmdir()  # only succeeds if empty
        except OSError:
            break
        parent = parent.parent


def _scan_stale_disk_repos(
    output_dir: Path, provenance_repo_ids: set[str]
) -> dict[str, list[Path]]:
    """Scan repos/ and mirrors/ for directories not backed by provenance.

    Returns a mapping of repo_id -> list of stale directory paths.
    Mirror bare clones use a .git suffix on the leaf directory.
    """
    stale: dict[str, list[Path]] = {}
    for subdir, suffix in (("repos", ""), ("mirrors", ".git")):
        root = output_dir / subdir
        if not root.exists():
            continue
        for source_dir in sorted(root.iterdir()):
            if not source_dir.is_dir():
                continue
            for owner_dir in sorted(source_dir.iterdir()):
                if not owner_dir.is_dir():
                    continue
                for leaf_dir in sorted(owner_dir.iterdir()):
                    if not leaf_dir.is_dir():
                        continue
                    name = leaf_dir.name
                    if suffix and name.endswith(suffix):
                        name = name[: -len(suffix)]
                    repo_id = "/".join(
                        [source_dir.name, owner_dir.name, name]
                    )
                    if repo_id not in provenance_repo_ids:
                        stale.setdefault(repo_id, []).append(leaf_dir)
    return stale


@app.command()
def cleanup(
    output_dir: Path = typer.Option(
        "cobol-corpus", "--output-dir", "-o", help="Corpus output directory"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List what would be cleaned without deleting"
    ),
) -> None:
    """Remove repos with zero COBOL files and clean stale disk directories."""
    setup_logging("INFO")
    data_dir = output_dir / "data"

    if not data_dir.exists():
        typer.echo("No corpus data found at: %s" % output_dir)
        raise typer.Exit(1)

    state = StateManager(data_dir)
    try:
        # Repos that have provenance -- we never touch these
        provenance_repo_ids = {
            r[0]
            for r in state.con.execute(
                "SELECT DISTINCT repo_id FROM file_provenance"
            ).fetchall()
        }

        # Done repos with zero provenance -> mark rejected
        rejectable = set(state.get_rejectable_repos())

        # Scan disk for stale directories (no provenance backing)
        stale = _scan_stale_disk_repos(output_dir, provenance_repo_ids)

        # Combine: any repo in rejectable or with stale dirs
        all_cleanable = rejectable | set(stale.keys())

        if not all_cleanable:
            typer.echo("No repos to clean up.")
            return

        if dry_run:
            typer.echo("Dry run -- would clean %d repos:" % len(all_cleanable))
            for repo_id in sorted(all_cleanable):
                label = "reject" if repo_id in rejectable else "clean disk"
                typer.echo("  [%s] %s" % (label, repo_id))
            return

        rejected_count = 0
        cleaned_count = 0
        for repo_id in sorted(all_cleanable):
            # Delete disk directories found by scan
            for dir_path in stale.get(repo_id, []):
                stop_at = dir_path.parent.parent.parent  # e.g. repos/ or mirrors/
                _remove_dir_and_prune_parents(dir_path, stop_at)
                log.info("Deleted %s", dir_path)

            # Also check canonical paths for rejectable repos without scan hits
            if repo_id in rejectable and repo_id not in stale:
                repos_path = output_dir / "repos" / repo_id
                mirrors_path = output_dir / "mirrors" / (repo_id + ".git")
                for p in (repos_path, mirrors_path):
                    if p.exists():
                        stop_at = p.parent.parent.parent
                        _remove_dir_and_prune_parents(p, stop_at)
                        log.info("Deleted %s", p)

            if repo_id in rejectable:
                state.set_repo_status(repo_id, "rejected")
                log.info("Rejected %s", repo_id)
                rejected_count += 1
            else:
                cleaned_count += 1

        state.flush()
        parts = []
        if rejected_count:
            parts.append("Rejected %d repos" % rejected_count)
        if cleaned_count:
            parts.append("cleaned %d stale directories" % cleaned_count)
        typer.echo(". ".join(parts) + ".")
    finally:
        state.close()


@app.command()
def purge(
    output_dir: Path = typer.Option(
        "cobol-corpus", "--output-dir", "-o", help="Corpus output directory"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="List what would be purged without deleting"
    ),
) -> None:
    """Remove files that fail content validation (binary, wrong format, multi-extension)."""
    from .extract.cobol_filter import has_multi_extension, is_binary_file, looks_like_cobol

    setup_logging("INFO")
    data_dir = output_dir / "data"

    if not data_dir.exists():
        typer.echo("No corpus data found at: %s" % output_dir)
        raise typer.Exit(1)

    state = StateManager(data_dir)
    repos_dir = output_dir / "repos"

    try:
        rows = state.con.execute(
            "SELECT sha256, repo_id, original_path FROM file_provenance"
        ).fetchall()

        purged_count = 0
        affected_repos: set[str] = set()

        for file_sha256, repo_id, original_path in rows:
            disk_path = repos_dir / repo_id / original_path

            if not disk_path.exists():
                continue

            reason = None
            if has_multi_extension(disk_path):
                reason = "multi-extension"
            elif is_binary_file(disk_path):
                reason = "binary"
            else:
                try:
                    content = disk_path.read_text(errors="replace")
                    if not looks_like_cobol(content):
                        reason = "non-COBOL content"
                except OSError:
                    reason = "unreadable"

            if reason is None:
                continue

            if dry_run:
                typer.echo("  [%s] %s/%s" % (reason, repo_id, original_path))
            else:
                disk_path.unlink(missing_ok=True)
                state.remove_provenance(file_sha256, repo_id)
                state.remove_file_if_orphaned(file_sha256)
                log.info("Purged %s/%s (%s)", repo_id, original_path, reason)

            purged_count += 1
            affected_repos.add(repo_id)

        if not dry_run:
            state.flush()

        if purged_count == 0:
            typer.echo("No files to purge.")
        elif dry_run:
            typer.echo("Dry run: would purge %d files from %d repos" % (purged_count, len(affected_repos)))
        else:
            typer.echo("Purged %d files from %d repos" % (purged_count, len(affected_repos)))
    finally:
        state.close()


@app.command()
def evaluate(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Evaluate repo quality using scc metrics and flag low-value repos."""
    import csv
    import io

    cfg = load_config(config_path)
    setup_logging(cfg.log_level)
    eval_cfg = cfg.evaluate

    base_dir = Path(cfg.output_dir)
    repos_dir = base_dir / "repos"
    data_dir = base_dir / "data"

    if not repos_dir.exists():
        typer.echo("No repos directory found at: %s" % repos_dir)
        raise typer.Exit(1)

    state = StateManager(data_dir) if data_dir.exists() else None

    # Discover repo directories on disk: repos/{source}/{owner}/{name} or repos/{source}/{owner}
    repo_dirs: list[tuple[str, Path]] = []
    for source_dir in sorted(repos_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        for owner_dir in sorted(source_dir.iterdir()):
            if not owner_dir.is_dir():
                continue
            # Check if owner_dir contains files directly (flat repo) or has sub-dirs (owner/name)
            has_sub_repos = any(
                d.is_dir() and not d.name.startswith(".")
                for d in owner_dir.iterdir()
            )
            if has_sub_repos:
                for name_dir in sorted(owner_dir.iterdir()):
                    if not name_dir.is_dir():
                        continue
                    repo_id = "%s/%s/%s" % (source_dir.name, owner_dir.name, name_dir.name)
                    repo_dirs.append((repo_id, name_dir))
            else:
                repo_id = "%s/%s" % (source_dir.name, owner_dir.name)
                repo_dirs.append((repo_id, owner_dir))

    if not repo_dirs:
        typer.echo("No repo directories found under %s" % repos_dir)
        raise typer.Exit(0)

    log.info("Evaluating %d repos", len(repo_dirs))
    results = []

    for repo_id, repo_path in repo_dirs:
        log.debug("Evaluating %s", repo_id)
        try:
            metadata = None
            if state is not None:
                row = state.con.execute(
                    "SELECT stars, description, is_fork FROM repos WHERE repo_id = ?",
                    [repo_id],
                ).fetchone()
                if row is not None:
                    metadata = RepoMetadata(
                        stars=row[0] or 0,
                        description=row[1] or "",
                        is_fork=bool(row[2]),
                        repo_name=repo_id,
                    )
            ev = evaluate_repo(
                repo_path, repo_id, eval_cfg.training_keywords,
                metadata=metadata, anti_keywords=eval_cfg.training_keywords,
            )
            results.append(ev)

            if state is not None:
                repo_exists = state.get_repo_status(repo_id) is not None
                if repo_exists:
                    state.upsert_evaluation(
                        repo_id=repo_id,
                        quality_score=ev.quality_score,
                        cobol_files=ev.scc.cobol_files,
                        cobol_code_lines=ev.scc.cobol_code_lines,
                        cobol_complexity=ev.scc.cobol_complexity,
                        training_flag=ev.training_flag,
                    )
        except Exception as exc:
            log.error("Failed evaluating %s: %s", repo_id, exc)

    # Sort by score descending
    results.sort(key=lambda r: r.quality_score, reverse=True)

    # Print report table
    header = "%-50s %5s %6s %8s %6s %5s %5s" % (
        "REPO", "SCORE", "FILES", "CODE", "CMPLX", "TRAIN", "JCL",
    )
    typer.echo(header)
    typer.echo("-" * len(header))
    for ev in results:
        flag = "Y" if ev.training_flag else ""
        jcl = str(ev.scc.jcl_files) if ev.scc.jcl_files > 0 else ""
        typer.echo("%-50s %5d %6d %8d %6d %5s %5s" % (
            ev.repo_id[:50],
            ev.quality_score,
            ev.scc.cobol_files,
            ev.scc.cobol_code_lines,
            ev.scc.cobol_complexity,
            flag,
            jcl,
        ))

    # Write CSV report if configured
    if eval_cfg.report_path:
        report_path = Path(eval_cfg.report_path)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "repo_id", "quality_score", "cobol_files", "cobol_code_lines",
            "cobol_comment_lines", "cobol_complexity", "jcl_files",
            "training_flag",
        ])
        for ev in results:
            writer.writerow([
                ev.repo_id, ev.quality_score, ev.scc.cobol_files,
                ev.scc.cobol_code_lines, ev.scc.cobol_comment_lines,
                ev.scc.cobol_complexity, ev.scc.jcl_files,
                ev.training_flag,
            ])
        report_path.write_text(buf.getvalue())
        typer.echo("\nReport written to %s" % report_path)

    # Auto-reject below threshold
    rejected_count = 0
    if not eval_cfg.dry_run and state is not None:
        for ev in results:
            if ev.quality_score < eval_cfg.threshold:
                current = state.get_repo_status(ev.repo_id)
                if current is not None and current != "rejected":
                    state.set_repo_status(ev.repo_id, "rejected")
                    rejected_count += 1

    # Summary
    above = sum(1 for ev in results if ev.quality_score >= eval_cfg.threshold)
    below = sum(1 for ev in results if ev.quality_score < eval_cfg.threshold)
    typer.echo("\nThreshold: %d" % eval_cfg.threshold)
    typer.echo("Above threshold: %d" % above)
    typer.echo("Below threshold: %d" % below)

    if eval_cfg.dry_run:
        typer.echo("Dry run -- no repos rejected")
    elif rejected_count > 0:
        typer.echo("Rejected %d repos" % rejected_count)

    if state is not None:
        state.flush()
        state.close()


@app.command()
def status(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Show corpus status and statistics."""
    cfg = load_config(config_path)
    base = Path(cfg.output_dir)
    data_dir = base / "data"

    if not data_dir.exists():
        typer.echo("No corpus data found at: %s" % base)
        raise typer.Exit(1)

    state = StateManager(data_dir)
    stats = state.get_stats()
    state.close()

    typer.echo("Corpus: %s" % base)
    typer.echo("Repos total: %d" % stats["repos_total"])
    typer.echo("  Done:     %d" % stats["repos_done"])
    typer.echo("  Failed:   %d" % stats["repos_failed"])
    typer.echo("  Rejected: %d" % stats["repos_rejected"])
    typer.echo("  Pending:  %d" % stats["repos_pending"])
    typer.echo("Unique files: %d" % stats["files_unique"])
    typer.echo("Provenance entries: %d" % stats["file_provenance_entries"])
    typer.echo("Total runs: %d" % stats["runs_total"])


@app.command()
def retry_failed(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Retry all previously failed repos."""
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)

    base_dir = Path(cfg.output_dir)
    orchestrator = CorpusOrchestrator(base_dir, cfg)

    try:
        failed = orchestrator.state.get_failed_repos()
        if not failed:
            log.info("No failed repos to retry")
            return

        log.info("Retrying %d failed repos", len(failed))
        for repo in failed:
            if orchestrator.shutdown_requested:
                break
            orchestrator.state.set_repo_status(repo["id"], "discovered")
            orchestrator.process_repo(repo)

        orchestrator.finish()
    finally:
        orchestrator.close()


@app.command()
def reset(
    config_path: Path = typer.Option(
        "corpus_builder.toml", "--config", "-c", help="Path to config file"
    ),
    all_data: bool = typer.Option(
        False, "--all", help="Remove state, repos, mirrors, and working directories"
    ),
    state_only: bool = typer.Option(
        False, "--state-only", help="Remove only the data/ state directory"
    ),
    repos_only: bool = typer.Option(
        False, "--repos-only", help="Remove only repos/, mirrors/, and working/ directories"
    ),
    force: bool = typer.Option(
        False, "--force", help="Skip confirmation prompt"
    ),
) -> None:
    """Reset the corpus by removing state and/or repo data."""
    setup_logging("INFO")

    flags = [all_data, state_only, repos_only]
    if sum(flags) != 1:
        typer.echo("Error: specify exactly one of --all, --state-only, --repos-only")
        raise typer.Exit(1)

    cfg = load_config(config_path)
    base_dir = Path(cfg.output_dir)

    targets: list[Path] = []
    if state_only:
        targets.append(base_dir / "data")
    elif repos_only:
        for name in ("repos", "mirrors", "working"):
            targets.append(base_dir / name)
    else:  # --all
        for name in ("data", "repos", "mirrors", "working"):
            targets.append(base_dir / name)

    existing = [t for t in targets if t.exists()]
    if not existing:
        typer.echo("Nothing to remove -- no target directories exist.")
        return

    typer.echo("Will remove:")
    for t in existing:
        typer.echo("  %s" % t)

    if not force:
        confirm = typer.confirm("Proceed?")
        if not confirm:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    for t in existing:
        shutil.rmtree(t)
        log.info("Removed %s", t)

    typer.echo("Reset complete.")


def main() -> None:
    app()
