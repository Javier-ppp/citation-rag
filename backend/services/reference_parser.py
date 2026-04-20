import re
from typing import List, Dict, Optional

# Match IEEE reference entry start e.g. "[1] Smith J..."
REF_ENTRY_PATTERN = re.compile(r'\[(\d+)\]\s+(.*?)(?=\[\d+\]|$)', re.DOTALL)

def extract_references_from_text(full_text: str) -> List[Dict[str, str]]:
    """
    Attempts to locate the References section and parse the entries.
    Returns a list of parsed references.
    """
    # Simple heuristic to find references section
    match = re.search(r'\n(References|Bibliography|REFERENCES)\n(.+)', full_text, flags=re.DOTALL)
    if not match:
        return []

    ref_text = match.group(2)
    entries = []
    
    for ref_match in REF_ENTRY_PATTERN.finditer(ref_text):
        ref_number = ref_match.group(1)
        raw_text = ref_match.group(2).strip().replace('\n', ' ')
        
        # Simple extraction heuristics (can be improved)
        parts = raw_text.split(',')
        first_author = parts[0].strip() if len(parts) > 0 else ""
        
        # Attempt to find year
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_text)
        year = year_match.group(1) if year_match else ""
        
        # Title heuristic
        title_match = re.search(r'["“](.*?)["”]', raw_text)
        title = title_match.group(1) if title_match else raw_text

        entries.append({
            "ref_number": ref_number,
            "raw_text": raw_text,
            "parsed_title": title,
            "parsed_first_author": first_author,
            "parsed_year": year
        })
        
    return entries
