from __future__ import annotations

import json
import logging
import math
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .extract.cobol_filter import is_cobol_file
from .extract.dialect import detect_dialect

log = logging.getLogger(__name__)


@dataclass
class SccStats:
    cobol_files: int = 0
    cobol_code_lines: int = 0
    cobol_comment_lines: int = 0
    cobol_blank_lines: int = 0
    cobol_complexity: int = 0
    jcl_files: int = 0


@dataclass
class RepoMetadata:
    stars: int = 0
    description: str = ""
    is_fork: bool = False
    repo_name: str = ""


@dataclass
class RepoEvaluation:
    repo_id: str
    scc: SccStats
    training_flag: bool
    quality_score: int


def run_scc(repo_path: Path) -> tuple[SccStats, list[dict]]:
    """Run scc on a repo directory and return parsed COBOL/JCL stats plus raw language list."""
    scc_bin = shutil.which("scc")
    if scc_bin is None:
        raise RuntimeError("scc is not installed or not on PATH")

    try:
        result = subprocess.run(
            [scc_bin, "--format", "json", str(repo_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        log.warning("scc timed out for %s", repo_path)
        return (SccStats(), [])

    if result.returncode != 0:
        log.warning("scc failed for %s: %s", repo_path, result.stderr.strip())
        return (SccStats(), [])

    stdout = result.stdout.strip()
    if not stdout:
        return (SccStats(), [])

    try:
        languages = json.loads(stdout)
    except json.JSONDecodeError:
        log.warning("scc returned invalid JSON for %s", repo_path)
        return (SccStats(), [])

    stats = SccStats()
    for lang in languages:
        name = lang.get("Name", "")
        if name == "COBOL":
            stats.cobol_files = lang.get("Count", 0)
            stats.cobol_code_lines = lang.get("Code", 0)
            stats.cobol_comment_lines = lang.get("Comment", 0)
            stats.cobol_blank_lines = lang.get("Blank", 0)
            stats.cobol_complexity = lang.get("Complexity", 0)
        elif name == "JCL":
            stats.jcl_files = lang.get("Count", 0)

    return (stats, languages)


def detect_training_paths(repo_path: Path, keywords: list[str]) -> bool:
    """Check if a majority of files live under training-related paths."""
    if not keywords:
        return False

    pattern = re.compile("|".join(re.escape(kw) for kw in keywords), re.IGNORECASE)
    total = 0
    matched = 0

    for f in repo_path.rglob("*"):
        if not f.is_file():
            continue
        total += 1
        rel = str(f.relative_to(repo_path))
        if pattern.search(rel):
            matched += 1

    if total == 0:
        return False

    return (matched / total) > 0.5


def _log_scale(value: float, zero_at: float, max_at: float, max_points: float) -> float:
    """Log-scaled scoring: 0 points at zero_at, max_points at max_at."""
    if value <= zero_at:
        return 0.0
    if value >= max_at:
        return max_points
    ratio = math.log(value / zero_at) / math.log(max_at / zero_at)
    return ratio * max_points


# ---------------------------------------------------------------------------
# New signal functions
# ---------------------------------------------------------------------------

def count_distinct_dialects(repo_path: Path) -> int:
    """Scan COBOL files and return count of distinct dialect tags found."""
    tags: set[str] = set()
    for f in repo_path.rglob("*"):
        if not f.is_file() or not is_cobol_file(f):
            continue
        try:
            content = f.read_text(errors="replace")
        except OSError:
            continue
        dialect_str = detect_dialect(content)
        if dialect_str:
            for tag in dialect_str.split(","):
                tag = tag.strip()
                if tag:
                    tags.add(tag)
    return len(tags)


_STRUCTURAL_PERFORM = re.compile(r"\bPERFORM\b", re.IGNORECASE)
_STRUCTURAL_CALL = re.compile(r"\bCALL\b", re.IGNORECASE)
_STRUCTURAL_COPY = re.compile(r"\bCOPY\b", re.IGNORECASE)


def analyze_structural_depth(repo_path: Path) -> int:
    """Score structural complexity based on PERFORM, CALL, COPY usage.

    Scoring: PERFORM present = 4pts, CALL = 3pts, COPY = 3pts.
    Frequency bonus: avg >= 10 per file = +3, >= 5 = +1.5, >= 2 = +0.5.
    Cap at 10 points.
    """
    has_perform = False
    has_call = False
    has_copy = False
    total_statements = 0
    file_count = 0

    for f in repo_path.rglob("*"):
        if not f.is_file() or not is_cobol_file(f):
            continue
        try:
            content = f.read_text(errors="replace")
        except OSError:
            continue
        file_count += 1
        perform_hits = len(_STRUCTURAL_PERFORM.findall(content))
        call_hits = len(_STRUCTURAL_CALL.findall(content))
        copy_hits = len(_STRUCTURAL_COPY.findall(content))

        if perform_hits > 0:
            has_perform = True
        if call_hits > 0:
            has_call = True
        if copy_hits > 0:
            has_copy = True

        total_statements += perform_hits + call_hits + copy_hits

    score = 0.0
    if has_perform:
        score += 4
    if has_call:
        score += 3
    if has_copy:
        score += 3

    if file_count > 0:
        avg = total_statements / file_count
        if avg >= 10:
            score += 3
        elif avg >= 5:
            score += 1.5
        elif avg >= 2:
            score += 0.5

    return min(10, int(round(score)))


_ECOSYSTEM_EXTENSIONS = {".bms", ".sql", ".ddl", ".rexx", ".rex", ".asm"}


def count_ecosystem_files(repo_path: Path, scc_languages: list[dict]) -> int:
    """Count non-COBOL supporting files and return a log-scaled score (0-10).

    Counts .bms, .sql, .ddl, .rexx, .rex, .asm files via direct scan,
    plus Assembly and SQL counts from scc output.
    """
    direct_count = 0
    for f in repo_path.rglob("*"):
        if f.is_file() and f.suffix.lower() in _ECOSYSTEM_EXTENSIONS:
            direct_count += 1

    # Also count from scc languages that might use different extensions
    scc_count = 0
    for lang in scc_languages:
        name = lang.get("Name", "")
        if name in ("Assembly", "SQL"):
            scc_count += lang.get("Count", 0)

    # Use the max of direct scan and scc count to avoid double-counting
    total = max(direct_count, scc_count)

    if total <= 0:
        return 0
    return int(round(_log_scale(total, 0.5, 10, 10)))


_DEFAULT_ANTI_KEYWORDS = ["hello", "demo", "sample", "tutorial", "exercise", "homework"]


def detect_anti_patterns(repo_id: str, keywords: list[str] | None = None) -> bool:
    """Check if repo name contains anti-pattern keywords.

    Extracts the last segment of repo_id (after the last /) and checks
    against keywords like hello, demo, sample, etc.
    """
    if keywords is None:
        keywords = _DEFAULT_ANTI_KEYWORDS
    name = repo_id.rsplit("/", 1)[-1].lower()
    return any(kw.lower() in name for kw in keywords)


_ENTERPRISE_KEYWORDS = [
    "enterprise", "mainframe", "cics", "banking", "legacy",
    "cobol", "batch", "db2", "vsam", "payroll",
]


def score_github_signals(metadata: RepoMetadata | None) -> int:
    """Score based on GitHub metadata: stars + description keywords.

    Stars: log scale 0-5 pts (0 at 0, 5 at 100+).
    Description keywords: 1pt each, max 5.
    Total cap at 10 points.
    Returns 0 if metadata is None.
    """
    if metadata is None:
        return 0

    score = 0.0

    # Stars: log scale 0-5
    if metadata.stars > 0:
        score += _log_scale(metadata.stars, 0.5, 100, 5)

    # Description keywords
    if metadata.description:
        desc_lower = metadata.description.lower()
        keyword_pts = sum(1 for kw in _ENTERPRISE_KEYWORDS if kw in desc_lower)
        score += min(5, keyword_pts)

    return min(10, int(round(score)))


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def compute_quality_score(
    scc: SccStats,
    training_flag: bool,
    repo_path: Path,
    scc_languages: list[dict],
    metadata: RepoMetadata | None = None,
    anti_keywords: list[str] | None = None,
) -> int:
    """Compute a 0-100 quality score from scc metrics, structural signals, and metadata."""
    score = 0.0

    # Code volume: 0-20 points (0 at <50 LOC, 20 at >=5000 LOC)
    score += _log_scale(scc.cobol_code_lines, 50, 5000, 20)

    # File breadth: 0-15 points (0 at 1 file, 15 at >=20 files)
    score += _log_scale(scc.cobol_files, 1, 20, 15)

    # Complexity: 0-10 points
    score += _log_scale(scc.cobol_complexity, 1, 100, 10)

    # JCL presence: 5 points
    if scc.jcl_files > 0:
        score += 5

    # Comment ratio: 0-5 points (peak at 15-30%)
    if scc.cobol_code_lines > 0:
        ratio = scc.cobol_comment_lines / (scc.cobol_code_lines + scc.cobol_comment_lines)
        if 0.15 <= ratio <= 0.30:
            score += 5
        elif 0.05 <= ratio < 0.15 or 0.30 < ratio <= 0.50:
            score += 2.5
        elif ratio > 0:
            score += 1

    # Average file size: 0-5 points (larger avg = more enterprise)
    if scc.cobol_files > 0:
        avg_loc = scc.cobol_code_lines / scc.cobol_files
        score += _log_scale(avg_loc, 20, 200, 5)

    # Dialect diversity: 0-10 points (2.5 pts per distinct dialect, capped at 10)
    dialect_count = count_distinct_dialects(repo_path)
    score += min(10, dialect_count * 2.5)

    # Structural depth: 0-10 points
    score += analyze_structural_depth(repo_path)

    # Ecosystem files: 0-10 points
    score += count_ecosystem_files(repo_path, scc_languages)

    # GitHub signals: 0-10 points
    score += score_github_signals(metadata)

    # --- Penalties ---
    if training_flag:
        score -= 20

    if scc.cobol_code_lines < 100:
        score -= 10

    # Fork penalty
    if metadata is not None and metadata.is_fork:
        score -= 15

    # Anti-pattern in repo name
    repo_id = metadata.repo_name if metadata else ""
    if repo_id and detect_anti_patterns(repo_id, anti_keywords):
        score -= 15

    # Single trivial file: 1 COBOL file + <50 LOC
    if scc.cobol_files == 1 and scc.cobol_code_lines < 50:
        score -= 10

    return max(0, min(100, int(round(score))))


def evaluate_repo(
    repo_path: Path,
    repo_id: str,
    training_keywords: list[str],
    metadata: RepoMetadata | None = None,
    anti_keywords: list[str] | None = None,
) -> RepoEvaluation:
    """Evaluate a single repo directory."""
    scc, scc_languages = run_scc(repo_path)
    training_flag = detect_training_paths(repo_path, training_keywords)

    if metadata is not None:
        metadata.repo_name = repo_id

    quality_score = compute_quality_score(
        scc, training_flag, repo_path, scc_languages,
        metadata=metadata, anti_keywords=anti_keywords,
    )

    return RepoEvaluation(
        repo_id=repo_id,
        scc=scc,
        training_flag=training_flag,
        quality_score=quality_score,
    )
