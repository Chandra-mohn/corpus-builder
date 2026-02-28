from __future__ import annotations

import json
import logging
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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
class RepoEvaluation:
    repo_id: str
    scc: SccStats
    training_flag: bool
    quality_score: int


def run_scc(repo_path: Path) -> SccStats:
    """Run scc on a repo directory and return parsed COBOL/JCL stats."""
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
        return SccStats()

    if result.returncode != 0:
        log.warning("scc failed for %s: %s", repo_path, result.stderr.strip())
        return SccStats()

    stdout = result.stdout.strip()
    if not stdout:
        return SccStats()

    try:
        languages = json.loads(stdout)
    except json.JSONDecodeError:
        log.warning("scc returned invalid JSON for %s", repo_path)
        return SccStats()

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

    return stats


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


def compute_quality_score(scc: SccStats, training_flag: bool) -> int:
    """Compute a 0-100 quality score from scc metrics and training flag."""
    score = 0.0

    # Code volume: 0-25 points (0 at <50 LOC, 25 at >=5000 LOC)
    score += _log_scale(scc.cobol_code_lines, 50, 5000, 25)

    # File breadth: 0-20 points (0 at 1 file, 20 at >=20 files)
    score += _log_scale(scc.cobol_files, 1, 20, 20)

    # Complexity: 0-15 points
    score += _log_scale(scc.cobol_complexity, 1, 100, 15)

    # JCL presence: 10 points
    if scc.jcl_files > 0:
        score += 10

    # Comment ratio: 0-10 points (peak at 15-30%)
    if scc.cobol_code_lines > 0:
        ratio = scc.cobol_comment_lines / (scc.cobol_code_lines + scc.cobol_comment_lines)
        if 0.15 <= ratio <= 0.30:
            score += 10
        elif 0.05 <= ratio < 0.15 or 0.30 < ratio <= 0.50:
            score += 5
        elif ratio > 0:
            score += 2

    # Average file size: 0-10 points (larger avg = more enterprise)
    if scc.cobol_files > 0:
        avg_loc = scc.cobol_code_lines / scc.cobol_files
        score += _log_scale(avg_loc, 20, 200, 10)

    # Penalties
    if training_flag:
        score -= 20

    if scc.cobol_code_lines < 100:
        score -= 10

    return max(0, min(100, int(round(score))))


def evaluate_repo(
    repo_path: Path,
    repo_id: str,
    training_keywords: list[str],
) -> RepoEvaluation:
    """Evaluate a single repo directory."""
    scc = run_scc(repo_path)
    training_flag = detect_training_paths(repo_path, training_keywords)
    quality_score = compute_quality_score(scc, training_flag)

    return RepoEvaluation(
        repo_id=repo_id,
        scc=scc,
        training_flag=training_flag,
        quality_score=quality_score,
    )
