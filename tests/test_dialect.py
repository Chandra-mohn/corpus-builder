from corpus_builder.extract.dialect import detect_dialect


def test_sql_detected():
    content = "EXEC SQL SELECT * FROM EMP END-EXEC"
    assert "SQL" in detect_dialect(content)


def test_cics_detected():
    content = "EXEC CICS SEND MAP END-EXEC"
    assert "CICS" in detect_dialect(content)


def test_dli_detected():
    content = "EXEC DLI GU SEGMENT(ROOT)"
    assert "DLI" in detect_dialect(content)


def test_ims_detected():
    content = "CALL 'CBLTDLI' USING FUNC PCB"
    assert "IMS" in detect_dialect(content)


def test_vsam_detected():
    content = "ORGANIZATION IS INDEXED"
    assert "VSAM" in detect_dialect(content)


def test_batch_detected():
    content = "SELECT PAYFILE ASSIGN TO PAYDATA"
    assert "BATCH" in detect_dialect(content)


def test_multiple_dialects():
    content = "EXEC SQL SELECT\nEXEC CICS SEND"
    tags = detect_dialect(content)
    assert "SQL" in tags
    assert "CICS" in tags


def test_case_insensitive():
    assert "SQL" in detect_dialect("exec sql select")
    assert "CICS" in detect_dialect("exec cics send")


def test_no_dialect():
    content = "MOVE A TO B.\nADD 1 TO COUNTER."
    assert detect_dialect(content) == ""


def test_empty_input():
    assert detect_dialect("") == ""
