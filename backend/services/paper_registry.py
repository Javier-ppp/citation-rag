import json
import os
import difflib
import re
from typing import Optional, Dict, Any

REGISTRY_PATH = "backend/data/paper_registry.json"

def _load_registry() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_PATH):
        return {}
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_registry(registry: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)

def register_paper(paper_id: str, metadata: Dict[str, Any]) -> None:
    """Registers a new ingested paper, ensuring only one 'main' paper exists."""
    registry = _load_registry()
    
    # If this paper is being registered as 'main', demote any current 'main' paper
    if metadata.get("role") == "main":
        for pid, meta in registry.items():
            if meta.get("role") == "main" and pid != paper_id:
                meta["role"] = "source"
                
    registry[paper_id] = metadata
    _save_registry(registry)

def get_paper(paper_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a paper by ID."""
    return _load_registry().get(paper_id)

def get_source_paper_ids() -> list[str]:
    """Returns a list of all paper IDs flagged as 'source'."""
    registry = _load_registry()
    return [pid for pid, meta in registry.items() if meta.get("role") == "source"]

def clean_title(t: str) -> str:
    """Removes common punctuation and noise for better fuzzy matching."""
    if not t: return ""
    # Strip quotes, dots, commas, extra spaces
    t = re.sub(r'["“\u201d\u201c\u2019\u2018\.\,]', '', t)
    return " ".join(t.lower().split())

def match_reference(parsed_ref: Dict[str, str]) -> Optional[str]:
    """
    Fuzzy matches a parsed reference against 'source' papers in the registry.
    """
    registry = _load_registry()
    if not registry:
        return None
        
    best_match = None
    best_score = 0.0
    
    ref_title = clean_title(parsed_ref.get("parsed_title", ""))
    if not ref_title:
        return None
    
    for pid, meta in registry.items():
        # ONLY match against source papers for backward mode
        if meta.get("role") != "source":
            continue
            
        meta_title = clean_title(meta.get("title", ""))
        if not meta_title:
            continue
            
        # Title ratio
        ratio = difflib.SequenceMatcher(None, ref_title, meta_title).ratio()
        
        # Boost score if year matches
        if meta.get("year") and str(meta.get("year")) == str(parsed_ref.get("parsed_year")):
            ratio += 0.1
            
        if ratio > best_score:
            best_score = ratio
            best_match = pid
            
    if best_score > 0.65:
        return best_match
    return None
