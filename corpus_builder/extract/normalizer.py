
def normalize_cobol(content: str) -> str:
    lines = []
    for line in content.splitlines():
        lines.append(line.rstrip())
    return "\n".join(lines)
