from corpus_builder.extract.normalizer import normalize_cobol


def test_preserves_original_content():
    raw = "000100 IDENTIFICATION DIVISION.\n000200 PROGRAM-ID. TEST."
    result = normalize_cobol(raw)
    assert result == "000100 IDENTIFICATION DIVISION.\n000200 PROGRAM-ID. TEST."


def test_short_lines_preserved():
    raw = "AB\nCDEF"
    result = normalize_cobol(raw)
    assert result == "AB\nCDEF"


def test_trailing_whitespace_stripped():
    raw = "000100 MOVE A TO B.   \n000200 STOP RUN.  "
    result = normalize_cobol(raw)
    lines = result.split("\n")
    for line in lines:
        assert line == line.rstrip()
    # Content (including sequence numbers) preserved
    assert "000100 MOVE A TO B." in result
    assert "000200 STOP RUN." in result


def test_empty_input():
    assert normalize_cobol("") == ""


def test_single_line():
    raw = "000100 IDENTIFICATION DIVISION."
    result = normalize_cobol(raw)
    assert result == "000100 IDENTIFICATION DIVISION."


def test_blank_lines_preserved():
    raw = "000100 DATA DIVISION.\n\n000300 WORKING-STORAGE SECTION."
    result = normalize_cobol(raw)
    assert "\n\n" in result
    assert "000100 DATA DIVISION." in result
    assert "000300 WORKING-STORAGE SECTION." in result
