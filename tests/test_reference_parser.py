import pytest
from backend.services.reference_parser import extract_references_from_text

def test_finds_references_section():
    text = '''
Some text here.
References
[1] J. Smith, "Great Title," Journal, 2020.
[2] A. Doe, "Another Paper," Conf., 2021.
'''
    refs = extract_references_from_text(text)
    assert len(refs) == 2
    assert refs[0]["ref_number"] == "1"
    assert refs[1]["ref_number"] == "2"

def test_parses_ieee_format():
    text = '''
References
[1] Smith, J., "Ocean Warming," J. Climate, 2019.
'''
    refs = extract_references_from_text(text)
    assert len(refs) == 1
    assert "Ocean Warming" in refs[0]["parsed_title"]
    assert refs[0]["parsed_year"] == "2019"

def test_handles_missing_references():
    text = "No ref section here. Just text."
    refs = extract_references_from_text(text)
    assert len(refs) == 0
