import pytest
import os
from backend.services.paper_registry import register_paper, get_paper, match_reference, _save_registry

@pytest.fixture(autouse=True)
def clean_registry():
    # Make sure we start fresh
    _save_registry({})
    yield
    _save_registry({})

def test_register_and_lookup():
    register_paper("123", {"title": "Ocean Warming Trends", "year": "2020"})
    paper = get_paper("123")
    assert paper is not None
    assert paper["title"] == "Ocean Warming Trends"

def test_fuzzy_match():
    register_paper("123", {"title": "Ocean Warming Trends", "year": "2020"})
    
    # Simulate a parsed reference that varies slightly
    ref = {
        "parsed_title": "ocean warming trend",
        "parsed_year": "2020"
    }
    matched_id = match_reference(ref)
    assert matched_id == "123"

def test_no_match_returns_none():
    register_paper("123", {"title": "Climate Info", "year": "2020"})
    ref = {
        "parsed_title": "Quantum Computing",
        "parsed_year": "2021"
    }
    assert match_reference(ref) is None
