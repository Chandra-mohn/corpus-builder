from corpus_builder.extract.format_detector import detect_source_format


class TestDirectiveDetection:
    def test_free_directive(self):
        content = "       >>SOURCE FORMAT IS FREE\n       IDENTIFICATION DIVISION.\n       PROGRAM-ID. TEST."
        assert detect_source_format(content) == "free"

    def test_fixed_directive(self):
        content = "       >>SOURCE FORMAT IS FIXED\n000100 IDENTIFICATION DIVISION.\n000200 PROGRAM-ID. TEST."
        assert detect_source_format(content) == "fixed"

    def test_directive_case_insensitive(self):
        content = "       >>source format is free\n       IDENTIFICATION DIVISION.\n       PROGRAM-ID. TEST."
        assert detect_source_format(content) == "free"

    def test_first_directive_wins(self):
        content = (
            "       >>SOURCE FORMAT IS FREE\n"
            "       >>SOURCE FORMAT IS FIXED\n"
            "       IDENTIFICATION DIVISION.\n"
        )
        assert detect_source_format(content) == "free"


class TestStatisticalDetection:
    def test_fixed_with_sequence_numbers(self):
        lines = [
            "000100 IDENTIFICATION DIVISION.",
            "000200 PROGRAM-ID. TEST.",
            "000300 DATA DIVISION.",
            "000400 WORKING-STORAGE SECTION.",
            "000500 PROCEDURE DIVISION.",
        ]
        content = "\n".join(lines)
        assert detect_source_format(content) == "fixed"

    def test_free_format_code(self):
        lines = [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. TEST.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "PROCEDURE DIVISION.",
        ]
        content = "\n".join(lines)
        assert detect_source_format(content) == "free"

    def test_fixed_with_comment_indicator(self):
        lines = [
            "000100 IDENTIFICATION DIVISION.",
            "000200*This is a comment",
            "000300 PROGRAM-ID. TEST.",
            "000400 DATA DIVISION.",
        ]
        content = "\n".join(lines)
        assert detect_source_format(content) == "fixed"


class TestEdgeCases:
    def test_empty_content(self):
        assert detect_source_format("") == "unknown"

    def test_single_line(self):
        assert detect_source_format("IDENTIFICATION DIVISION.") == "unknown"

    def test_two_lines(self):
        content = "000100 IDENTIFICATION DIVISION.\n000200 PROGRAM-ID. TEST."
        assert detect_source_format(content) == "unknown"

    def test_blank_lines_only(self):
        content = "\n\n\n"
        assert detect_source_format(content) == "unknown"

    def test_blank_lines_ignored_in_count(self):
        lines = [
            "000100 IDENTIFICATION DIVISION.",
            "",
            "000200 PROGRAM-ID. TEST.",
            "",
            "000300 DATA DIVISION.",
        ]
        content = "\n".join(lines)
        assert detect_source_format(content) == "fixed"
