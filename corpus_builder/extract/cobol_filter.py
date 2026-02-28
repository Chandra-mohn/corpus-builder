import re
from pathlib import Path

COBOL_EXTENSIONS = {
    ".cbl", ".cob", ".cpy",
    ".ccp", ".jcl", ".pco"
}

# Known non-COBOL extensions that indicate a multi-extension false positive
_NON_COBOL_EXTENSIONS = {
    ".json", ".xml", ".yaml", ".yml", ".html", ".csv", ".txt",
    ".js", ".py", ".java", ".c", ".h", ".cfg", ".ini", ".md",
    ".rst", ".sql", ".sh", ".bat", ".log", ".dat",
}

# COBOL structural keywords for content validation
_COBOL_KEYWORDS = re.compile(
    r"\b(?:"
    r"DIVISION|SECTION|PROCEDURE|WORKING-STORAGE|PIC|PERFORM|MOVE|COPY"
    r"|PROGRAM-ID|IDENTIFICATION|DATA|ENVIRONMENT|EVALUATE|END-IF|STOP\s+RUN"
    r")\b",
    re.IGNORECASE,
)


def is_cobol_file(path):
    return path.suffix.lower() in COBOL_EXTENSIONS


def has_multi_extension(path: Path) -> bool:
    """Reject files where a non-COBOL extension precedes the COBOL suffix.

    Examples: data.json.cpy -> True, PAYROLL.CBL -> False
    """
    stem = path.stem
    inner_ext = Path(stem).suffix.lower()
    if not inner_ext:
        return False
    return inner_ext in _NON_COBOL_EXTENSIONS


def is_binary_file(path: Path, sample_size: int = 8192) -> bool:
    """Return True if the file appears to be binary (contains null bytes)."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except OSError:
        return True


def looks_like_cobol(content: str) -> bool:
    """Return True if text content looks like COBOL source.

    Checks the first 4096 characters for COBOL structural keywords
    and rejects content that is clearly another format.
    """
    sample = content[:4096].lstrip()
    if not sample:
        return False

    # Reject obvious non-COBOL formats
    if sample[0] in ("{", "["):
        return False  # JSON
    if sample[0] == "<":
        return False  # XML/HTML
    if sample.startswith("#!"):
        return False  # Script shebang

    return _COBOL_KEYWORDS.search(sample) is not None
