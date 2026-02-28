from corpus_builder.extract.normalizer import normalize_cobol


def test_strips_sequence_numbers():
    raw = "000100 IDENTIFICATION DIVISION.\n000200 PROGRAM-ID. TEST."
    result = normalize_cobol(raw)
    assert result == " IDENTIFICATION DIVISION.\n PROGRAM-ID. TEST."


def test_short_lines_preserved():
    raw = "AB\nCDEF"
    result = normalize_cobol(raw)
    # Lines <= 6 chars are kept as-is (no stripping)
    assert result == "AB\nCDEF"


def test_trailing_whitespace_stripped():
    raw = "000100 MOVE A TO B.   \n000200 STOP RUN.  "
    result = normalize_cobol(raw)
    lines = result.split("\n")
    for line in lines:
        assert line == line.rstrip()


def test_empty_input():
    assert normalize_cobol("") == ""


def test_single_line():
    raw = "000100 IDENTIFICATION DIVISION."
    result = normalize_cobol(raw)
    assert result == " IDENTIFICATION DIVISION."


def test_blank_lines_preserved():
    raw = "000100 DATA DIVISION.\n\n000300 WORKING-STORAGE SECTION."
    result = normalize_cobol(raw)
    assert "\n\n" in result
