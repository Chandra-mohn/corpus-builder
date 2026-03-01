"""Detect whether COBOL source is fixed-format, free-format, or unknown."""

from __future__ import annotations

import re

_DIRECTIVE_RE = re.compile(
    r">>SOURCE\s+FORMAT\s+IS\s+(FREE|FIXED)", re.IGNORECASE
)

_SEQUENCE_NUMBER_RE = re.compile(r"^\d{6}$")

_FIXED_INDICATORS = frozenset(" *-/Dd")


def detect_source_format(content: str) -> str:
    """Return ``"fixed"``, ``"free"``, or ``"unknown"`` for *content*.

    Detection priority:
    1. Compiler directive ``>>SOURCE FORMAT IS FREE|FIXED`` (first wins).
    2. Statistical analysis of non-blank lines when no directive found.
    """
    # -- 1. directive check (authoritative) --
    for line in content.splitlines():
        m = _DIRECTIVE_RE.search(line)
        if m:
            return m.group(1).lower()

    # -- 2. statistical analysis --
    non_blank = [ln for ln in content.splitlines() if ln.strip()]
    if len(non_blank) < 3:
        return "unknown"

    fixed_signals = 0
    free_signals = 0

    for line in non_blank:
        if len(line) >= 7:
            cols_1_6 = line[:6]
            col_7 = line[6]

            if _SEQUENCE_NUMBER_RE.match(cols_1_6) and col_7 in _FIXED_INDICATORS:
                fixed_signals += 1
                continue

        # Free signals: code starts at column 1 (non-space, non-digit leader)
        if line and not line[0].isspace() and not _SEQUENCE_NUMBER_RE.match(line[:6]):
            free_signals += 1
            continue

        # Lines with meaningful content past column 72
        if len(line) > 72 and line[72:].strip():
            free_signals += 1

    total = len(non_blank)
    if fixed_signals / total >= 0.60:
        return "fixed"
    if free_signals / total >= 0.60:
        return "free"
    return "unknown"
