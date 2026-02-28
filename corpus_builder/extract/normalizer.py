
def normalize_cobol(content: str) -> str:
    lines = []
    for line in content.splitlines():
        if len(line) > 6:
            line = line[6:]
        lines.append(line.rstrip())
    return "\n".join(lines)
