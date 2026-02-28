from __future__ import annotations

import re

# Patterns that indicate specific COBOL environments/dialects
_DIALECT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CICS", re.compile(r"\bEXEC\s+CICS\b", re.IGNORECASE)),
    ("SQL", re.compile(r"\bEXEC\s+SQL\b", re.IGNORECASE)),
    ("DLI", re.compile(r"\bEXEC\s+DLI\b", re.IGNORECASE)),
    ("IMS", re.compile(r"\bCBLTDLI\b", re.IGNORECASE)),
    ("VSAM", re.compile(r"\bORGANIZATION\s+IS\s+INDEXED\b", re.IGNORECASE)),
    ("BATCH", re.compile(r"\bSELECT\s+\w+\s+ASSIGN\s+TO\b", re.IGNORECASE)),
]


def detect_dialect(content: str) -> str:
    """Scan COBOL source for dialect markers.

    Returns a comma-separated string of detected tags (e.g. "CICS,SQL").
    Returns empty string if no specific dialect markers found.
    """
    tags = []
    for tag, pattern in _DIALECT_PATTERNS:
        if pattern.search(content):
            tags.append(tag)
    return ",".join(tags)
