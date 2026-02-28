import tempfile
from pathlib import Path

from corpus_builder.extract.cobol_filter import (
    COBOL_EXTENSIONS,
    has_multi_extension,
    is_binary_file,
    is_cobol_file,
    looks_like_cobol,
)


def test_cobol_extensions_recognized():
    for ext in COBOL_EXTENSIONS:
        assert is_cobol_file(Path(f"test{ext}"))


def test_uppercase_extensions():
    assert is_cobol_file(Path("TEST.CBL"))
    assert is_cobol_file(Path("TEST.COB"))


def test_non_cobol_rejected():
    assert not is_cobol_file(Path("test.py"))
    assert not is_cobol_file(Path("test.java"))
    assert not is_cobol_file(Path("test.txt"))
    assert not is_cobol_file(Path("Makefile"))


def test_no_extension_rejected():
    assert not is_cobol_file(Path("README"))


# -- has_multi_extension --


def test_multi_ext_json_cpy():
    assert has_multi_extension(Path("data.json.cpy"))


def test_multi_ext_xml_cbl():
    assert has_multi_extension(Path("config.xml.cbl"))


def test_multi_ext_normal_cobol():
    assert not has_multi_extension(Path("PAYROLL.CBL"))


def test_multi_ext_single_dot_in_stem_unknown():
    # "my.cbl" -- stem is "my", no inner extension
    assert not has_multi_extension(Path("my.cbl"))


def test_multi_ext_unknown_inner_ext():
    # "data.zzz.cpy" -- inner ext .zzz is not in the known list
    assert not has_multi_extension(Path("data.zzz.cpy"))


# -- is_binary_file --


def test_binary_file_with_null_bytes():
    with tempfile.NamedTemporaryFile(suffix=".cbl", delete=False) as f:
        f.write(b"some data\x00more data")
        f.flush()
        assert is_binary_file(Path(f.name))


def test_text_file_not_binary():
    with tempfile.NamedTemporaryFile(suffix=".cbl", mode="w", delete=False) as f:
        f.write("IDENTIFICATION DIVISION.\nPROGRAM-ID. TEST.\n")
        f.flush()
        assert not is_binary_file(Path(f.name))


def test_binary_nonexistent_file():
    assert is_binary_file(Path("/nonexistent/path.cbl"))


# -- looks_like_cobol --


def test_looks_like_cobol_valid():
    content = (
        "000100 IDENTIFICATION DIVISION.\n"
        "000200 PROGRAM-ID. PAYROLL.\n"
        "000300 PROCEDURE DIVISION.\n"
        "000400     STOP RUN.\n"
    )
    assert looks_like_cobol(content)


def test_looks_like_cobol_json():
    assert not looks_like_cobol('{"key": "value"}')


def test_looks_like_cobol_json_array():
    assert not looks_like_cobol('[1, 2, 3]')


def test_looks_like_cobol_xml():
    assert not looks_like_cobol('<?xml version="1.0"?><root/>')


def test_looks_like_cobol_html():
    assert not looks_like_cobol('<html><body>hello</body></html>')


def test_looks_like_cobol_shebang():
    assert not looks_like_cobol('#!/bin/bash\necho "hello"')


def test_looks_like_cobol_python():
    # No COBOL keywords present
    assert not looks_like_cobol('def main():\n    print("hello")\n')


def test_looks_like_cobol_empty():
    assert not looks_like_cobol("")


def test_looks_like_cobol_whitespace_only():
    assert not looks_like_cobol("   \n\n  ")


def test_looks_like_cobol_case_insensitive():
    assert looks_like_cobol("identification division.\nprogram-id. test.\n")
