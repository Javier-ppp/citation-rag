import re
import json
import logging
from typing import List, Dict, Optional
from backend.services.llm_client import generate_response

logger = logging.getLogger(__name__)

# Match IEEE reference entry start e.g. "[1] Smith J..."
REF_ENTRY_PATTERN = re.compile(r'\[(\d+)\]\s+(.*?)(?=\[\d+\]|$)', re.DOTALL)

async def extract_references_llm(full_text: str) -> List[Dict[str, str]]:
    """
    Finds the References section and uses LLM to parse entries precisely.
    """
    match = re.search(r'\n(References|Bibliography|REFERENCES)\s*\n(.+)', full_text, flags=re.DOTALL)
    if not match:
        logger.warning("[REF_PARSER] References section not found in text.")
        return []

    ref_text = match.group(2).strip()
    
    prompt = (
        f"Parse the following academic references into a structured JSON list.\n"
        f"For each entry, extract: 'ref_number', 'parsed_title', 'parsed_first_author', 'parsed_year'.\n"
        f"References:\n{ref_text[:5000]}"
    )
    
    try:
        response = await generate_response(prompt)
        # Find JSON block
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        logger.error(f"[REF_PARSER] LLM extraction failed: {e}")
        
    # Fallback to simple regex if LLM fails
    return extract_references_from_text(full_text)

def extract_references_from_text(full_text: str) -> List[Dict[str, str]]:
    """
    Simple heuristic fallback.
    """
    match = re.search(r'\n(References|Bibliography|REFERENCES)\n(.+)', full_text, flags=re.DOTALL)
    if not match:
        return []

    ref_text = match.group(2)
    entries = []
    
    for ref_match in REF_ENTRY_PATTERN.finditer(ref_text):
        ref_number = ref_match.group(1)
        raw_text = ref_match.group(2).strip().replace('\n', ' ')
        
        parts = raw_text.split(',')
        first_author = parts[0].strip() if len(parts) > 0 else ""
        
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_text)
        year = year_match.group(1) if year_match else ""
        
        title_match = re.search(r'["“\u201d\u201c](.*?)[”\u201d\u201c"]', raw_text)
        title = title_match.group(1) if title_match else raw_text

        entries.append({
            "ref_number": ref_number,
            "raw_text": raw_text,
            "parsed_title": title.strip(),
            "parsed_first_author": first_author,
            "parsed_year": year
        })
        
    return entries
