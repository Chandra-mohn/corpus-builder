# corpus_builder -- Production-Ready Specification

## Overview

A tool for discovering, cloning, and extracting COBOL source files from public
repositories to build a deduplicated, research-grade corpus.

## Use Cases

- Research and analysis of COBOL codebases
- Code search and reference for legacy system work

## Requirements Summary

| Dimension        | Decision                                                    |
|------------------|-------------------------------------------------------------|
| Scale            | Thousands of repos, tens of thousands of COBOL files        |
| Runtime          | Local workstation                                           |
| Resumability     | Critical -- flush state after every repo completes          |
| Sources          | Pluggable adapter system (GitHub + Software Heritage + more)|
| Metadata         | Rich (license, stars, last commit, file paths, COBOL dialect)|
| Dedup            | Global across all repos, with provenance tracking           |
| Storage          | DuckDB query engine + Parquet files as source of truth      |
| Packaging        | uv + pyproject.toml                                         |
| Testing          | Comprehensive (unit + integration + mocked APIs + edge cases)|
| Rate limiting    | Built-in with automatic backoff and retry                   |

## Data Architecture

### Storage Model

Parquet files are the persistent source of truth. DuckDB is used as the query
engine -- reads Parquet at run start, operates on in-memory tables, flushes
back to Parquet after every repo completes.

```
cobol-corpus/
  data/
    repos.parquet
    files.parquet
    file_provenance.parquet
    runs.parquet
    ref_file_types.parquet
    ref_dialect_tags.parquet
  repos/               # COBOL files in original directory structure
    github/
      owner/repo-name/
        src/PAYROLL.CBL
        copybooks/COMMON.CPY
    software_heritage/
      owner/repo-name/
        COB/MAIN.COB
  mirrors/             # bare git clones
    github/
      owner/repo-name.git/
```

### Entity Relationship Diagram

```
+-------------------------+
|          runs           |
+-------------------------+
| run_id (PK)             |
| started_at              |
| finished_at             |
| config_snapshot         |
| repos_processed         |
| repos_failed            |
| files_extracted         |
+-------------------------+
         |
         | referenced by (1:N)
         |
+-------------------------+       +----------------------+       +------------------+
|         repos           |--1:N--| file_provenance      |--N:1--| files            |
+-------------------------+       +----------------------+       +------------------+
| repo_id (PK)            |       | sha256 (FK -> files) |       | sha256 (PK)      |
| clone_url               |       | repo_id (FK -> repos)|       | store_path       |
| source                  |       | run_id (FK -> runs)  |       | byte_size        |
| status                  |       | original_path        |       | line_count       |
| error_msg               |       | extracted_at         |       | file_type        |
| license_spdx            |       +----------------------+       | dialect_tags     |
| stars                   |                                      | first_seen_at    |
|                         |                                      +------------------+
| description             |
| default_branch          |
| last_pushed_at          |
| discovered_at           |
| completed_at            |
| last_run_id (FK -> runs)|
| repo_size_kb            |
+-------------------------+
```

Relationships:
- repos <-> files: many-to-many via file_provenance
- runs -> repos: one-to-many via repos.last_run_id
- runs -> file_provenance: one-to-many via file_provenance.run_id

### Schema: runs

Audit log of each execution. Referenced by repos and file_provenance.

| Column          | Type               | Notes                              |
|-----------------|--------------------|------------------------------------|
| run_id          | string             | PK. UUID                           |
| started_at      | timestamp          | run start                          |
| finished_at     | timestamp (nullable)| run end                           |
| config_snapshot | string             | JSON of config used                |
| repos_processed | int                | count of repos completed           |
| repos_failed    | int                | count of repos failed              |
| files_extracted | int                | count of unique files added        |

### Schema: repos

Tracks every discovered repository and its processing status.

| Column          | Type               | Notes                              |
|-----------------|--------------------|------------------------------------|
| repo_id         | string             | PK. e.g. `github/owner/repo-name` |
| clone_url       | string             | git clone URL                      |
| source          | string             | `github`, `software_heritage`      |
| status          | string             | discovered/cloning/cloned/extracting/done/failed |
| error_msg       | string (nullable)  | failure reason if status=failed    |
| license_spdx    | string (nullable)  | e.g. `MIT`, `GPL-3.0`             |
| stars           | int (nullable)     | stargazers count                   |
| description     | string (nullable)  | repo description                   |
| default_branch  | string (nullable)  | e.g. `main`                        |
| last_pushed_at  | timestamp (nullable)| last push date from source API    |
| discovered_at   | timestamp          | when adapter found it              |
| completed_at    | timestamp (nullable)| when extraction finished           |
| last_run_id     | string (nullable)  | FK -> runs. most recent run that touched this repo |
| repo_size_kb    | int (nullable)     | repo size in KB (from source API)  |

### Schema: files

Every unique COBOL file in the corpus, identified by content hash. Files are stored
on disk with their original filenames and directory structure under repos/.

| Column          | Type               | Notes                              |
|-----------------|--------------------|------------------------------------|
| sha256          | string             | PK. hash of normalized content     |
| store_path      | string             | relative path in repos dir         |
| byte_size       | int                | size of normalized file            |
| line_count      | int                | lines in normalized file           |
| file_type       | string             | file extension (e.g. cbl, cpy, jcl)|
| dialect_tags    | string             | comma-separated: CICS,SQL,BATCH    |
| first_seen_at   | timestamp          | when first extracted               |

### Schema: file_provenance

Many-to-many junction between files and repos. Largest table.

| Column          | Type               | Notes                              |
|-----------------|--------------------|------------------------------------|
| sha256          | string             | FK -> files                        |
| repo_id         | string             | FK -> repos                        |
| run_id          | string             | FK -> runs. which run extracted it |
| original_path   | string             | path within the source repo        |
| extracted_at    | timestamp          | when this copy was extracted       |

### Schema: ref_file_types

Static lookup table describing known COBOL/mainframe file extensions.

| Column          | Type               | Notes                              |
|-----------------|--------------------|----------------------------------  |
| extension       | string             | PK. e.g. `cbl`, `cpy`, `jcl`      |
| description     | string             | human-readable description         |

### Schema: ref_dialect_tags

Static lookup table describing COBOL dialect tags assigned by dialect detection.

| Column          | Type               | Notes                              |
|-----------------|--------------------|------------------------------------|
| tag             | string             | PK. e.g. `CICS`, `SQL`, `BATCH`   |
| description     | string             | human-readable description         |

### Example Queries

```sql
-- What did run X extract?
SELECT r.repo_id, f.sha256, fp.original_path
FROM file_provenance fp
JOIN repos r ON r.repo_id = fp.repo_id
JOIN files f ON f.sha256 = fp.sha256
WHERE fp.run_id = 'run-uuid-here';

-- How many repos share a given file?
SELECT COUNT(DISTINCT repo_id)
FROM file_provenance WHERE sha256 = 'abc123...';

-- Most common COBOL dialects
SELECT dialect_tags, COUNT(*) AS cnt
FROM files GROUP BY dialect_tags ORDER BY cnt DESC;

-- Failed repos from last run
SELECT repo_id, error_msg
FROM repos WHERE last_run_id = 'run-uuid' AND status = 'failed';
```

## CLI Commands

| Command                | Description                                           |
|------------------------|-------------------------------------------------------|
| `corpus-builder discover` | Discover repos from source APIs, populate manifest |
| `corpus-builder extract`  | Extract COBOL files from incomplete repos in manifest |
| `corpus-builder run`      | Convenience: discover + extract in a single pass   |
| `corpus-builder status`   | Show corpus statistics                             |
| `corpus-builder retry-failed` | Retry all previously failed repos              |

The two-phase workflow (`discover` then `extract`) lets users review the repo
manifest in DBeaver before committing to extraction. The `run` command preserves
the original single-pass behavior.

## Pipeline

### Phase 1: Discovery (`corpus-builder discover`)

```
Source adapters query APIs
       |
Yield repo metadata (id, clone_url, license, stars, repo_size_kb, ...)
       |
Upsert into repos table (preserves 'done' status on re-discovery)
       |
Flush manifest to repos.parquet
```

### Phase 2: Extraction (`corpus-builder extract`)

```
1. Query repos WHERE status NOT IN ('done')
       |
2. Clone (mirror)    (git clone --mirror, skip if already cloned)
       |
3. Checkout          (checkout working tree from bare mirror)
       |
4. Filter            (walk files, match COBOL extensions)
       |
5. Normalize         (strip sequence number columns, trailing whitespace)
       |
6. Hash + Dedup      (SHA-256 normalized content, skip if hash exists)
       |
7. Detect dialect    (scan for EXEC SQL, EXEC CICS, etc.)
       |
8. Store             (write to repos/{repo_id}/{original_path})
       |
9. Record provenance (file -> repo mapping, deduplicated per repo)
       |
10. Flush state      (write all tables to Parquet after each repo)
```

## Project Structure

```
corpus_builder/
  __init__.py
  cli.py                   # typer CLI entry point
  config.py                # TOML config loading
  orchestrator.py           # main pipeline
  state.py                 # DuckDB + Parquet state manager
  rate_limiter.py           # token-bucket rate limiter
  sources/
    __init__.py
    base.py                # SourceAdapter ABC
    github.py              # GitHub search API adapter
    software_heritage.py   # SWH API adapter
    registry.py            # adapter registry
  extract/
    __init__.py
    cobol_filter.py        # file extension matching
    normalizer.py          # COBOL column stripping
    hasher.py              # SHA-256 hashing
    dialect.py             # COBOL dialect detection
  vcs/
    __init__.py
    git_tools.py           # git clone --mirror
tests/
  test_normalizer.py
  test_filter.py
  test_hasher.py
  test_dialect.py
  test_state.py
  test_rate_limiter.py
  test_github_adapter.py
  test_pipeline.py         # integration
  test_discover.py         # discover command + idempotency
  fixtures/                # mock API responses, test COBOL files
pyproject.toml
corpus_builder.toml        # default config example
```

## Implementation Phases

### Phase 1: Foundation
- pyproject.toml with uv, dependencies (requests, duckdb, typer, pyarrow)
- TOML config file replacing hardcoded values
- CLI via typer: `corpus-builder run`, `corpus-builder status`
- Structured logging (Python logging module)

### Phase 2: State & Resumability
- DuckDB + Parquet state manager (StateManager class)
- Read Parquet at startup, operate in-memory, flush after each repo
- Orchestrator refactored to check/update status per repo
- Resume-from-failure: query repos WHERE status NOT IN ('done')

### Phase 3: Global Dedup & Rich Metadata
- Original directory structure: repos/{repo_id}/{original_path}
- Provenance tracking in file_provenance table
- Extend GitHub adapter: license, stars, last_pushed_at, description
- COBOL dialect detection (EXEC SQL, EXEC CICS, EXEC DLI, COPY)
- Retire index/repo_index.py

### Phase 4: Reliability
- Token-bucket rate limiter per adapter
- Exponential backoff + jitter on 403/429/5xx
- Per-repo error isolation (try/except, mark failed, continue)
- `corpus-builder retry-failed` CLI command
- Graceful shutdown: SIGINT handler, flush state, mark in-progress for retry

### Phase 5: Pluggable Adapter System
- Adapter registry with config-driven enable/disable
- Wire in SoftwareHeritageAdapter
- Per-adapter config sections in TOML
- Adapter template documentation

### Phase 6: Comprehensive Testing
- Unit: normalizer, filter, hasher, dialect, state manager, rate limiter
- Mocked API: GitHub adapter with fixture responses (pagination, errors, rate limits)
- Integration: end-to-end pipeline with mock adapter + tiny test git repo
- Edge cases: empty repos, binary files, encoding issues, huge files, no COBOL files

### Implementation Order

1 -> 2 -> 4 -> 3 -> 5 -> 6

(Tests written alongside each phase, not deferred.)
