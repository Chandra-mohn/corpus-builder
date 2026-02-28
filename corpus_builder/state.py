from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

TABLES = ("runs", "repos", "files", "file_provenance", "ref_file_types", "ref_dialect_tags")

CREATE_STMTS = {
    "runs": """
        CREATE TABLE IF NOT EXISTS runs (
            run_id          VARCHAR PRIMARY KEY,
            started_at      TIMESTAMP NOT NULL,
            finished_at     TIMESTAMP,
            config_snapshot VARCHAR,
            repos_processed INTEGER DEFAULT 0,
            repos_failed    INTEGER DEFAULT 0,
            files_extracted INTEGER DEFAULT 0
        )
    """,
    "repos": """
        CREATE TABLE IF NOT EXISTS repos (
            repo_id         VARCHAR PRIMARY KEY,
            clone_url       VARCHAR NOT NULL,
            source          VARCHAR NOT NULL,
            status          VARCHAR NOT NULL DEFAULT 'discovered',
            error_msg       VARCHAR,
            license_spdx    VARCHAR,
            stars           INTEGER,
            description     VARCHAR,
            default_branch  VARCHAR,
            last_pushed_at  TIMESTAMP,
            discovered_at   TIMESTAMP NOT NULL,
            completed_at    TIMESTAMP,
            last_run_id     VARCHAR,
            repo_size_kb    INTEGER,
            quality_score       INTEGER,
            cobol_files         INTEGER,
            cobol_code_lines    INTEGER,
            cobol_complexity    INTEGER,
            training_flag       BOOLEAN,
            evaluated_at        TIMESTAMP
        )
    """,
    "files": """
        CREATE TABLE IF NOT EXISTS files (
            sha256        VARCHAR PRIMARY KEY,
            store_path    VARCHAR NOT NULL,
            byte_size     INTEGER NOT NULL,
            line_count    INTEGER NOT NULL,
            file_type     VARCHAR NOT NULL,
            dialect_tags  VARCHAR DEFAULT '',
            first_seen_at TIMESTAMP NOT NULL
        )
    """,
    "file_provenance": """
        CREATE TABLE IF NOT EXISTS file_provenance (
            sha256        VARCHAR NOT NULL,
            repo_id       VARCHAR NOT NULL,
            run_id        VARCHAR NOT NULL,
            original_path VARCHAR NOT NULL,
            extracted_at  TIMESTAMP NOT NULL
        )
    """,
    "ref_file_types": """
        CREATE TABLE IF NOT EXISTS ref_file_types (
            extension   VARCHAR PRIMARY KEY,
            description VARCHAR NOT NULL
        )
    """,
    "ref_dialect_tags": """
        CREATE TABLE IF NOT EXISTS ref_dialect_tags (
            tag         VARCHAR PRIMARY KEY,
            description VARCHAR NOT NULL
        )
    """,
}


REF_FILE_TYPES = [
    ("cbl", "COBOL source program"),
    ("cob", "COBOL source program (alternate convention)"),
    ("cpy", "COBOL copybook (reusable data/code include)"),
    ("ccp", "COBOL copybook (alternate convention)"),
    ("pco", "Pro*COBOL source (Oracle embedded SQL preprocessor)"),
    ("sqb", "COBOL source with embedded SQL (DB2 preprocessor)"),
    ("jcl", "Job Control Language (batch job definition)"),
    ("bms", "Basic Mapping Support (CICS screen map definition)"),
    ("mfs", "IMS Message Format Service definition"),
    ("psb", "IMS Program Specification Block"),
    ("dbd", "IMS Database Descriptor"),
]

REF_DIALECT_TAGS = [
    ("CICS", "Customer Information Control System -- IBM online transaction processing"),
    ("SQL", "Embedded SQL -- typically IBM DB2 relational database access"),
    ("DLI", "Data Language/I -- IMS hierarchical database query interface"),
    ("IMS", "Information Management System -- IBM hierarchical database and message queuing"),
    ("VSAM", "Virtual Storage Access Method -- IBM indexed and sequential file access"),
    ("BATCH", "Batch processing -- sequential file I/O with ACCEPT, DISPLAY, STOP RUN"),
]


class StateManager:
    """Manages pipeline state using DuckDB in-memory with Parquet persistence."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(":memory:")
        self._load()
        self._init_ref_tables()

    def _load(self) -> None:
        for table in TABLES:
            parquet_path = self.data_dir / f"{table}.parquet"
            if parquet_path.exists():
                log.info("Loading %s from %s", table, parquet_path)
                cols = [
                    col[0]
                    for col in self.con.execute(
                        f"SELECT name FROM parquet_schema('{parquet_path}')"
                    ).fetchall()
                ]
                if table == "files" and "file_type" not in cols:
                    log.warning("Migrating files table: adding file_type column")
                    self.con.execute(
                        f"CREATE TABLE {table} AS "
                        f"SELECT *, 'unknown' AS file_type FROM read_parquet('{parquet_path}')"
                    )
                elif table == "repos" and "repo_size_kb" not in cols:
                    log.warning("Migrating repos table: adding repo_size_kb column")
                    self.con.execute(
                        f"CREATE TABLE {table} AS "
                        f"SELECT *, NULL::INTEGER AS repo_size_kb FROM read_parquet('{parquet_path}')"
                    )
                elif table == "repos" and "quality_score" not in cols:
                    log.warning("Migrating repos table: adding evaluation columns")
                    self.con.execute(
                        f"CREATE TABLE {table} AS "
                        f"SELECT *, NULL::INTEGER AS quality_score, "
                        f"NULL::INTEGER AS cobol_files, "
                        f"NULL::INTEGER AS cobol_code_lines, "
                        f"NULL::INTEGER AS cobol_complexity, "
                        f"NULL::BOOLEAN AS training_flag, "
                        f"NULL::TIMESTAMP AS evaluated_at "
                        f"FROM read_parquet('{parquet_path}')"
                    )
                else:
                    self.con.execute(
                        f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{parquet_path}')"
                    )
            else:
                log.info("Creating empty table: %s", table)
                self.con.execute(CREATE_STMTS[table])

    def _init_ref_tables(self) -> None:
        for table, data in [
            ("ref_file_types", REF_FILE_TYPES),
            ("ref_dialect_tags", REF_DIALECT_TAGS),
        ]:
            count = self.con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if count == 0:
                self.con.executemany(
                    f"INSERT INTO {table} VALUES (?, ?)", data
                )
                log.info("Populated %s with %d entries", table, len(data))

    def flush(self) -> None:
        for table in TABLES:
            parquet_path = self.data_dir / f"{table}.parquet"
            count = self.con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            if count > 0:
                self.con.execute(
                    f"COPY {table} TO '{parquet_path}' (FORMAT parquet, OVERWRITE true)"
                )
            elif parquet_path.exists():
                parquet_path.unlink()
        log.debug("State flushed to Parquet")

    def close(self) -> None:
        self.flush()
        self.con.close()

    # -- runs --

    def create_run(self, run_id: str, config_snapshot: str) -> None:
        now = _now()
        self.con.execute(
            "INSERT INTO runs (run_id, started_at, config_snapshot) VALUES (?, ?, ?)",
            [run_id, now, config_snapshot],
        )

    def finish_run(
        self, run_id: str, repos_processed: int, repos_failed: int, files_extracted: int
    ) -> None:
        self.con.execute(
            """UPDATE runs
               SET finished_at = ?, repos_processed = ?, repos_failed = ?, files_extracted = ?
               WHERE run_id = ?""",
            [_now(), repos_processed, repos_failed, files_extracted, run_id],
        )

    # -- repos --

    def upsert_repo(self, repo_meta: dict, run_id: str | None) -> bool:
        """Upsert a repo. Returns True if this was a new insert, False if update."""
        row = self.con.execute(
            "SELECT repo_id, status FROM repos WHERE repo_id = ?", [repo_meta["id"]]
        ).fetchone()

        now = _now()
        if row:
            current_status = row[1]
            if current_status in ("done", "rejected"):
                # Preserve done/rejected status -- only update metadata
                self.con.execute(
                    """UPDATE repos SET
                       license_spdx = COALESCE(?, license_spdx),
                       stars = COALESCE(?, stars),
                       description = COALESCE(?, description),
                       default_branch = COALESCE(?, default_branch),
                       repo_size_kb = COALESCE(?, repo_size_kb),
                       last_run_id = COALESCE(?, last_run_id)
                       WHERE repo_id = ?""",
                    [
                        repo_meta.get("license_spdx"),
                        repo_meta.get("stars"),
                        repo_meta.get("description"),
                        repo_meta.get("default_branch"),
                        repo_meta.get("repo_size_kb"),
                        run_id,
                        repo_meta["id"],
                    ],
                )
            else:
                # Reset to discovered for non-done repos
                self.con.execute(
                    """UPDATE repos SET status = 'discovered', error_msg = NULL,
                       license_spdx = COALESCE(?, license_spdx),
                       stars = COALESCE(?, stars),
                       description = COALESCE(?, description),
                       default_branch = COALESCE(?, default_branch),
                       repo_size_kb = COALESCE(?, repo_size_kb),
                       last_run_id = COALESCE(?, last_run_id)
                       WHERE repo_id = ?""",
                    [
                        repo_meta.get("license_spdx"),
                        repo_meta.get("stars"),
                        repo_meta.get("description"),
                        repo_meta.get("default_branch"),
                        repo_meta.get("repo_size_kb"),
                        run_id,
                        repo_meta["id"],
                    ],
                )
            return False
        else:
            self.con.execute(
                """INSERT INTO repos
                   (repo_id, clone_url, source, status, license_spdx, stars,
                    description, default_branch, last_pushed_at, discovered_at,
                    last_run_id, repo_size_kb)
                   VALUES (?, ?, ?, 'discovered', ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    repo_meta["id"],
                    repo_meta["clone_url"],
                    repo_meta["source"],
                    repo_meta.get("license_spdx"),
                    repo_meta.get("stars"),
                    repo_meta.get("description"),
                    repo_meta.get("default_branch"),
                    repo_meta.get("last_pushed_at"),
                    now,
                    run_id,
                    repo_meta.get("repo_size_kb"),
                ],
            )
            return True

    def set_repo_status(
        self, repo_id: str, status: str, error_msg: str | None = None
    ) -> None:
        if status == "done":
            self.con.execute(
                "UPDATE repos SET status = ?, error_msg = NULL, completed_at = ? WHERE repo_id = ?",
                [status, _now(), repo_id],
            )
        elif status == "failed":
            self.con.execute(
                "UPDATE repos SET status = ?, error_msg = ? WHERE repo_id = ?",
                [status, error_msg, repo_id],
            )
        else:
            self.con.execute(
                "UPDATE repos SET status = ? WHERE repo_id = ?",
                [status, repo_id],
            )

    def get_repo_status(self, repo_id: str) -> str | None:
        row = self.con.execute(
            "SELECT status FROM repos WHERE repo_id = ?", [repo_id]
        ).fetchone()
        return row[0] if row else None

    def get_incomplete_repos(self) -> list[dict]:
        rows = self.con.execute(
            """SELECT repo_id, clone_url, source
               FROM repos WHERE status NOT IN ('done', 'rejected')
               ORDER BY discovered_at"""
        ).fetchall()
        return [
            {"id": r[0], "clone_url": r[1], "source": r[2]} for r in rows
        ]

    def get_failed_repos(self) -> list[dict]:
        rows = self.con.execute(
            """SELECT repo_id, clone_url, source, error_msg
               FROM repos WHERE status = 'failed'
               ORDER BY discovered_at"""
        ).fetchall()
        return [
            {"id": r[0], "clone_url": r[1], "source": r[2], "error_msg": r[3]}
            for r in rows
        ]

    def get_rejectable_repos(self) -> list[str]:
        """Return repo_ids that are 'done' but have zero files in provenance."""
        rows = self.con.execute(
            """SELECT r.repo_id
               FROM repos r
               LEFT JOIN file_provenance fp ON r.repo_id = fp.repo_id
               WHERE r.status = 'done'
               GROUP BY r.repo_id
               HAVING count(fp.sha256) = 0"""
        ).fetchall()
        return [r[0] for r in rows]

    # -- evaluation --

    def upsert_evaluation(
        self,
        repo_id: str,
        quality_score: int,
        cobol_files: int,
        cobol_code_lines: int,
        cobol_complexity: int,
        training_flag: bool,
    ) -> None:
        self.con.execute(
            """UPDATE repos SET
               quality_score = ?, cobol_files = ?, cobol_code_lines = ?,
               cobol_complexity = ?, training_flag = ?, evaluated_at = ?
               WHERE repo_id = ?""",
            [quality_score, cobol_files, cobol_code_lines,
             cobol_complexity, training_flag, _now(), repo_id],
        )

    def get_evaluated_repos(self) -> list[dict]:
        rows = self.con.execute(
            """SELECT repo_id, quality_score, cobol_files, cobol_code_lines,
                      cobol_complexity, training_flag
               FROM repos WHERE evaluated_at IS NOT NULL
               ORDER BY quality_score DESC"""
        ).fetchall()
        return [
            {
                "repo_id": r[0], "quality_score": r[1], "cobol_files": r[2],
                "cobol_code_lines": r[3], "cobol_complexity": r[4],
                "training_flag": r[5],
            }
            for r in rows
        ]

    # -- files --

    def file_exists(self, file_hash: str) -> bool:
        row = self.con.execute(
            "SELECT 1 FROM files WHERE sha256 = ?", [file_hash]
        ).fetchone()
        return row is not None

    def add_file(
        self,
        file_hash: str,
        store_path: str,
        byte_size: int,
        line_count: int,
        file_type: str = "unknown",
        dialect_tags: str = "",
    ) -> None:
        self.con.execute(
            """INSERT INTO files (sha256, store_path, byte_size, line_count, file_type, dialect_tags, first_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [file_hash, store_path, byte_size, line_count, file_type, dialect_tags, _now()],
        )

    # -- file_provenance --

    def add_provenance(
        self, file_hash: str, repo_id: str, run_id: str, original_path: str
    ) -> None:
        existing = self.con.execute(
            "SELECT 1 FROM file_provenance WHERE sha256 = ? AND repo_id = ?",
            [file_hash, repo_id],
        ).fetchone()
        if existing:
            return
        self.con.execute(
            """INSERT INTO file_provenance (sha256, repo_id, run_id, original_path, extracted_at)
               VALUES (?, ?, ?, ?, ?)""",
            [file_hash, repo_id, run_id, original_path, _now()],
        )

    def remove_provenance(self, sha256: str, repo_id: str) -> None:
        """Delete a specific provenance entry."""
        self.con.execute(
            "DELETE FROM file_provenance WHERE sha256 = ? AND repo_id = ?",
            [sha256, repo_id],
        )

    def remove_file_if_orphaned(self, sha256: str) -> bool:
        """Delete from files table if no provenance entries remain.

        Returns True if the file record was deleted.
        """
        count = self.con.execute(
            "SELECT count(*) FROM file_provenance WHERE sha256 = ?", [sha256]
        ).fetchone()[0]
        if count == 0:
            self.con.execute("DELETE FROM files WHERE sha256 = ?", [sha256])
            return True
        return False

    # -- stats --

    def get_stats(self) -> dict:
        repos_total = self.con.execute("SELECT count(*) FROM repos").fetchone()[0]
        repos_done = self.con.execute(
            "SELECT count(*) FROM repos WHERE status = 'done'"
        ).fetchone()[0]
        repos_failed = self.con.execute(
            "SELECT count(*) FROM repos WHERE status = 'failed'"
        ).fetchone()[0]
        repos_rejected = self.con.execute(
            "SELECT count(*) FROM repos WHERE status = 'rejected'"
        ).fetchone()[0]
        files_total = self.con.execute("SELECT count(*) FROM files").fetchone()[0]
        provenance_total = self.con.execute(
            "SELECT count(*) FROM file_provenance"
        ).fetchone()[0]
        runs_total = self.con.execute("SELECT count(*) FROM runs").fetchone()[0]

        return {
            "repos_total": repos_total,
            "repos_done": repos_done,
            "repos_failed": repos_failed,
            "repos_rejected": repos_rejected,
            "repos_pending": repos_total - repos_done - repos_failed - repos_rejected,
            "files_unique": files_total,
            "file_provenance_entries": provenance_total,
            "runs_total": runs_total,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)
