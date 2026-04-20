import pytest
import os
import fitz
from backend.services.pdf_parser import extract_citations, parse_pdf

def test_citation_regex_finds_brackets():
    text = "as shown [1] and [2, 3] and also [4-6]"
    citations = extract_citations(text)
    markers = [c.marker for c in citations]
    assert "[1]" in markers
    assert "[2, 3]" in markers
    assert "[4-6]" in markers

def test_citation_regex_ignores_equations():
    text = "solve [x + y = 0] and be happy"
    citations = extract_citations(text)
    assert len(citations) == 0

def test_extract_text_dummy(tmp_path):
    # Creates a dummy PDF to test parser
    pdf_path = tmp_path / "dummy.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World [1]")
    doc.save(pdf_path)
    
    res = parse_pdf(str(pdf_path))
    assert res["num_pages"] == 1
    assert "Hello World" in res["pages"][0].text
    assert len(res["pages"][0].citations) == 1
    assert res["pages"][0].citations[0].marker == "[1]"
