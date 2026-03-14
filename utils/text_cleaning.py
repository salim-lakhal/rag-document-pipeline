"""
Text cleaning and preprocessing utilities for document processing.

This module provides functions for cleaning, normalizing, and preprocessing text
from various document formats. It handles boilerplate removal, whitespace
normalization, language detection, and date standardization.
"""

import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    Detect the language of the given text using langdetect.

    Args:
        text: Input text to detect language from

    Returns:
        ISO 639-1 language code (e.g., 'en', 'fr', 'es')
        Returns 'unknown' if detection fails

    Examples:
        >>> detect_language("This is an English sentence.")
        'en'
        >>> detect_language("Ceci est une phrase française.")
        'fr'
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for language detection")
        return "unknown"

    try:
        from langdetect import LangDetectException, detect

        # Use only first 1000 characters for efficiency
        sample_text = text[:1000].strip()
        if len(sample_text) < 10:
            logger.warning("Text too short for reliable language detection")
            return "unknown"

        detected_lang = detect(sample_text)
        logger.debug(f"Detected language: {detected_lang}")
        return detected_lang

    except LangDetectException as e:
        logger.error(f"Language detection failed: {e}")
        return "unknown"
    except ImportError:
        logger.error("langdetect library not installed. Install with: pip install langdetect")
        return "unknown"
    except Exception as e:
        logger.error(f"Unexpected error in language detection: {e}")
        return "unknown"


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text by standardizing spaces, newlines, and tabs.

    - Replaces multiple spaces with single space
    - Normalizes line breaks (handles \\r\\n, \\r, \\n)
    - Removes leading/trailing whitespace from lines
    - Collapses multiple blank lines into maximum of 2
    - Removes tabs and replaces with spaces

    Args:
        text: Input text with potentially inconsistent whitespace

    Returns:
        Text with normalized whitespace

    Examples:
        >>> normalize_whitespace("Hello    world\\n\\n\\n\\nNext paragraph")
        'Hello world\\n\\nNext paragraph'
    """
    if not text:
        return ""

    # Replace tabs with spaces
    text = text.replace('\t', ' ')

    # Normalize line endings (Windows \\r\\n, old Mac \\r, Unix \\n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove multiple spaces (but preserve newlines)
    text = re.sub(r' +', ' ', text)

    # Strip whitespace from each line
    lines = [line.strip() for line in text.split('\n')]

    # Collapse multiple blank lines to maximum of 2
    result_lines = []
    blank_count = 0

    for line in lines:
        if line:
            result_lines.append(line)
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)

    # Join lines and ensure no trailing whitespace
    normalized = '\n'.join(result_lines).strip()

    return normalized


def remove_boilerplate(text: str) -> str:
    """
    Remove common boilerplate content from documents.

    Removes:
    - Page headers and footers (page numbers, dates, document titles)
    - Repeated legal disclaimers
    - Standard headers that appear multiple times
    - Common footer patterns
    - Document metadata patterns

    Args:
        text: Input text potentially containing boilerplate

    Returns:
        Text with boilerplate removed

    Examples:
        >>> text = "Page 1 of 10\\nActual content\\nPage 2 of 10\\nMore content"
        >>> remove_boilerplate(text)
        'Actual content\\nMore content'
    """
    if not text:
        return ""

    # Common boilerplate patterns
    boilerplate_patterns = [
        # Page numbers
        r'^Page\s+\d+\s+of\s+\d+\s*$',
        r'^\d+\s*/\s*\d+\s*$',
        r'^-\s*\d+\s*-\s*$',

        # Headers and footers with dates
        r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$',
        r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+.*\d{4}\s*$',

        # Document metadata
        r'^(?:Confidential|Internal|Draft|DRAFT)\s*$',
        r'^(?:Document|File)\s+(?:ID|Number)[:]\s*\S+\s*$',

        # Common repeated headers
        r'^={3,}\s*$',
        r'^-{3,}\s*$',
        r'^_{3,}\s*$',

        # Legal boilerplate markers
        r'^©\s*\d{4}.*$',
        r'^Copyright\s+©.*$',
        r'^All rights reserved\.?\s*$',
    ]

    lines = text.split('\n')
    cleaned_lines = []

    # Compile patterns for efficiency
    compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                         for pattern in boilerplate_patterns]

    for line in lines:
        stripped_line = line.strip()

        # Skip empty lines (will be handled by whitespace normalization)
        if not stripped_line:
            cleaned_lines.append(line)
            continue

        # Check if line matches any boilerplate pattern
        is_boilerplate = any(pattern.match(stripped_line)
                            for pattern in compiled_patterns)

        if not is_boilerplate:
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # Remove repeated identical lines (common in headers/footers)
    result = _remove_repeated_lines(result)

    return result


def _remove_repeated_lines(text: str, min_repetitions: int = 3) -> str:
    """
    Remove lines that are repeated multiple times consecutively.

    Args:
        text: Input text
        min_repetitions: Minimum number of repetitions to consider removal

    Returns:
        Text with repeated lines removed
    """
    lines = text.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        current_line = lines[i]

        # Count consecutive repetitions
        repetitions = 1
        while (i + repetitions < len(lines) and
               lines[i + repetitions].strip() == current_line.strip() and
               current_line.strip()):
            repetitions += 1

        # If line is repeated many times, keep only one instance
        if repetitions >= min_repetitions:
            result_lines.append(current_line)
            i += repetitions
        else:
            # Keep all instances if below threshold
            for _ in range(repetitions):
                result_lines.append(current_line)
            i += repetitions

    return '\n'.join(result_lines)


def remove_duplicates(text: str) -> str:
    """
    Remove duplicate paragraphs from text while preserving order.

    Considers paragraphs as duplicates if they are exactly the same
    (after stripping whitespace). Preserves the first occurrence.

    Args:
        text: Input text potentially containing duplicate paragraphs

    Returns:
        Text with duplicate paragraphs removed

    Examples:
        >>> text = "First para.\\n\\nSecond para.\\n\\nFirst para."
        >>> remove_duplicates(text)
        'First para.\\n\\nSecond para.'
    """
    if not text:
        return ""

    # Split into paragraphs (separated by blank lines)
    paragraphs = re.split(r'\n\s*\n', text)

    seen = set()
    unique_paragraphs = []

    for para in paragraphs:
        # Normalize paragraph for comparison
        normalized = para.strip()

        # Skip empty paragraphs
        if not normalized:
            continue

        # Keep paragraph if not seen before
        if normalized not in seen:
            seen.add(normalized)
            unique_paragraphs.append(para.strip())

    # Rejoin with double newlines to preserve paragraph structure
    result = '\n\n'.join(unique_paragraphs)

    logger.debug(f"Removed {len(paragraphs) - len(unique_paragraphs)} duplicate paragraphs")

    return result


def standardize_dates(text: str) -> str:
    """
    Standardize various date formats to a consistent ISO format (YYYY-MM-DD).

    Handles common date formats:
    - DD/MM/YYYY, MM/DD/YYYY
    - DD-MM-YYYY, MM-DD-YYYY
    - DD.MM.YYYY
    - Month DD, YYYY
    - DD Month YYYY

    Args:
        text: Input text containing various date formats

    Returns:
        Text with dates standardized to YYYY-MM-DD format

    Examples:
        >>> standardize_dates("Meeting on 15/03/2024 and 03/15/2024")
        'Meeting on 2024-03-15 and 2024-03-15'
    """
    if not text:
        return ""

    result = text

    # Pattern for DD/MM/YYYY or MM/DD/YYYY (with /, -, or .)
    # Converts to YYYY-MM-DD, attempting DD/MM/YYYY interpretation first
    date_patterns = [
        # DD/MM/YYYY format (European style)
        (r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b',
         lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),

        # YYYY/MM/DD format (ISO-like with different separators)
        (r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b',
         lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"),
    ]

    # Month name patterns (e.g., "15 March 2024" or "March 15, 2024")
    month_names = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
        # French months
        'janvier': '01', 'janv': '01',
        'février': '02', 'fevrier': '02', 'fév': '02', 'fev': '02',
        'mars': '03',
        'avril': '04', 'avr': '04',
        'mai': '05',
        'juin': '06',
        'juillet': '07', 'juil': '07',
        'août': '08', 'aout': '08',
        'septembre': '09',
        'octobre': '10',
        'novembre': '11',
        'décembre': '12', 'decembre': '12', 'déc': '12',
    }

    # Replace month names with numbers
    # Pattern: "15 March 2024" or "March 15, 2024"
    for month_name, month_num in month_names.items():
        # Day Month Year (e.g., "15 March 2024")
        pattern1 = re.compile(
            rf'\b(\d{{1,2}})\s+{re.escape(month_name)}\s+(\d{{4}})\b',
            re.IGNORECASE
        )
        result = pattern1.sub(rf'\2-{month_num}-\1', result)

        # Month Day, Year (e.g., "March 15, 2024")
        pattern2 = re.compile(
            rf'\b{re.escape(month_name)}\s+(\d{{1,2}}),?\s+(\d{{4}})\b',
            re.IGNORECASE
        )
        result = pattern2.sub(rf'\2-{month_num}-\1', result)

    # Apply numeric date patterns
    for pattern, replacement in date_patterns:
        result = re.sub(pattern, replacement, result)

    # Ensure all dates have zero-padded days and months
    result = re.sub(
        r'\b(\d{4})-(\d)-(\d)\b',
        lambda m: f"{m.group(1)}-0{m.group(2)}-0{m.group(3)}",
        result
    )
    result = re.sub(
        r'\b(\d{4})-(\d)-(\d{2})\b',
        lambda m: f"{m.group(1)}-0{m.group(2)}-{m.group(3)}",
        result
    )
    result = re.sub(
        r'\b(\d{4})-(\d{2})-(\d)\b',
        lambda m: f"{m.group(1)}-{m.group(2)}-0{m.group(3)}",
        result
    )

    return result


def clean_text(text: str) -> str:
    """
    Comprehensive text cleaning pipeline combining all cleaning functions.

    Applies the following operations in order:
    1. Remove boilerplate content
    2. Normalize whitespace
    3. Remove duplicate paragraphs
    4. Standardize date formats

    Args:
        text: Raw input text to clean

    Returns:
        Cleaned and normalized text

    Examples:
        >>> raw = "Page 1\\n\\nHello    world\\n\\n\\n\\nHello world\\n\\nDate: 15/03/2024"
        >>> clean = clean_text(raw)
    """
    if not text:
        logger.warning("Empty text provided to clean_text")
        return ""

    try:
        # Step 1: Remove boilerplate
        logger.debug("Removing boilerplate content")
        text = remove_boilerplate(text)

        # Step 2: Normalize whitespace
        logger.debug("Normalizing whitespace")
        text = normalize_whitespace(text)

        # Step 3: Remove duplicates
        logger.debug("Removing duplicate paragraphs")
        text = remove_duplicates(text)

        # Step 4: Standardize dates
        logger.debug("Standardizing date formats")
        text = standardize_dates(text)

        # Final whitespace cleanup
        text = text.strip()

        logger.info(f"Text cleaning complete. Final length: {len(text)} characters")
        return text

    except Exception as e:
        logger.error(f"Error during text cleaning: {e}")
        # Return original text if cleaning fails
        return text


if __name__ == "__main__":
    # Example usage and testing
    sample_text = """
    Page 1 of 10

    This is a sample document with    multiple   spaces.



    This paragraph appears twice.

    Meeting scheduled for 15/03/2024 and March 20, 2024.

    This paragraph appears twice.

    Copyright © 2024 Company Name
    All rights reserved.
    """

    print("Original text:")
    print(sample_text)
    print("\n" + "="*50 + "\n")

    cleaned = clean_text(sample_text)
    print("Cleaned text:")
    print(cleaned)
    print("\n" + "="*50 + "\n")

    language = detect_language(cleaned)
    print(f"Detected language: {language}")
