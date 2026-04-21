import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from backend.models import Page, Citation

# Regex for IEEE style citations: [1], [1, 2], [1-5]
CITATION_PATTERN = re.compile(r'\[\s*([\d,\s\-–]+)\s*\]')

def extract_citations(text: str) -> List[Citation]:
    """Finds all IEEE citation markers in text and returns them with position."""
    citations = []
    for match in CITATION_PATTERN.finditer(text):
        citations.append(Citation(marker=match.group(0), position=match.start()))
    return citations

def parse_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Parses a PDF file from a given path.
    Returns the parsed pages containing text and found citation markers.
    """
    pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc):
            # Use "text" with sort=True to ensure top-to-bottom reading order
            text = page.get_text("text", sort=True)
            citations = extract_citations(text)
            pages.append(Page(page_num=page_num, text=text, citations=citations))
        
        return {
            "num_pages": len(doc),
            "pages": pages,
            "metadata_hint": pages[0].text[:2000] if pages else ""
        }
    except Exception as e:
        raise ValueError(f"Failed to parse PDF {pdf_path}: {str(e)}")
