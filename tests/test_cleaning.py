from utils.text_cleaning import (
    clean_text,
    detect_language,
    normalize_whitespace,
    remove_boilerplate,
    remove_duplicates,
    standardize_dates,
)


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("hello    world") == "hello world"

    def test_normalizes_line_endings(self):
        result = normalize_whitespace("line1\r\nline2\rline3")
        assert "\r" not in result
        assert "line1" in result and "line2" in result and "line3" in result

    def test_collapses_blank_lines(self):
        result = normalize_whitespace("a\n\n\n\n\nb")
        assert result.count("\n") <= 3

    def test_strips_line_whitespace(self):
        result = normalize_whitespace("  hello  \n  world  ")
        assert result == "hello\nworld"

    def test_replaces_tabs(self):
        assert "\t" not in normalize_whitespace("hello\tworld")

    def test_empty_input(self):
        assert normalize_whitespace("") == ""
        assert normalize_whitespace(None) == ""


class TestRemoveBoilerplate:
    def test_removes_page_numbers(self):
        text = "Page 1 of 10\nActual content\nPage 2 of 10"
        result = remove_boilerplate(text)
        assert "Page 1 of 10" not in result
        assert "Actual content" in result

    def test_removes_dash_page_numbers(self):
        text = "Content here\n- 5 -\nMore content"
        result = remove_boilerplate(text)
        assert "- 5 -" not in result
        assert "Content here" in result

    def test_removes_copyright(self):
        text = "Content\n© 2024 Company\nAll rights reserved."
        result = remove_boilerplate(text)
        assert "©" not in result
        assert "All rights reserved" not in result

    def test_removes_separator_lines(self):
        text = "Above\n==========\nBelow"
        result = remove_boilerplate(text)
        assert "==========" not in result

    def test_preserves_content(self):
        text = "This is important content that should stay."
        assert text in remove_boilerplate(text)

    def test_empty_input(self):
        assert remove_boilerplate("") == ""


class TestRemoveDuplicates:
    def test_removes_duplicate_paragraphs(self):
        text = "First para.\n\nSecond para.\n\nFirst para."
        result = remove_duplicates(text)
        assert result.count("First para.") == 1
        assert "Second para." in result

    def test_preserves_order(self):
        text = "A\n\nB\n\nC\n\nA"
        result = remove_duplicates(text)
        parts = [p.strip() for p in result.split("\n\n")]
        assert parts == ["A", "B", "C"]

    def test_empty_input(self):
        assert remove_duplicates("") == ""


class TestStandardizeDates:
    def test_european_date_format(self):
        result = standardize_dates("Date: 15/03/2024")
        assert "2024-03-15" in result

    def test_dot_separator(self):
        result = standardize_dates("Date: 15.03.2024")
        assert "2024-03-15" in result

    def test_english_month_name(self):
        result = standardize_dates("Date: 15 March 2024")
        assert "2024-03-15" in result

    def test_english_month_name_reversed(self):
        result = standardize_dates("Date: March 15, 2024")
        assert "2024-03-15" in result

    def test_french_month_name(self):
        result = standardize_dates("Date: 15 janvier 2024")
        assert "2024-01-15" in result

    def test_iso_format_preserved(self):
        result = standardize_dates("Already ISO: 2024/03/15")
        assert "2024-03-15" in result

    def test_empty_input(self):
        assert standardize_dates("") == ""

    def test_no_dates(self):
        text = "No dates here."
        assert standardize_dates(text) == text


class TestCleanText:
    def test_full_pipeline(self):
        raw = "Page 1 of 10\n\nHello    world\n\n\n\nHello world\n\nDate: 15/03/2024"
        result = clean_text(raw)
        assert "Page 1 of 10" not in result
        assert "2024-03-15" in result
        assert "Hello world" in result

    def test_empty_input(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_preserves_meaningful_content(self):
        text = "This is a meaningful paragraph about immigration procedures."
        result = clean_text(text)
        assert "immigration procedures" in result


class TestDetectLanguage:
    def test_detects_english(self):
        text = "This is a long enough English text for language detection to work properly."
        assert detect_language(text) == "en"

    def test_detects_french(self):
        text = "Ceci est un texte suffisamment long en français pour que la détection fonctionne."
        assert detect_language(text) == "fr"

    def test_empty_returns_unknown(self):
        assert detect_language("") == "unknown"
        assert detect_language("   ") == "unknown"

    def test_short_text_returns_unknown(self):
        assert detect_language("Hi") == "unknown"
