import json
import os
import difflib
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
    """Registers a new ingested paper."""
    registry = _load_registry()
    registry[paper_id] = metadata
    _save_registry(registry)

def get_paper(paper_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a paper by ID."""
    return _load_registry().get(paper_id)

def match_reference(parsed_ref: Dict[str, str]) -> Optional[str]:
    """
    Fuzzy matches a parsed reference against the registry.
    Looks for overlap in title, and verifies author or year.
    Returns paper_id if found, else None.
    """
    registry = _load_registry()
    if not registry:
        return None
        
    best_match = None
    best_score = 0.0
    
    ref_title = parsed_ref.get("parsed_title", "").lower()
    
    for pid, meta in registry.items():
        meta_title = meta.get("title", "").lower()
        if not meta_title or not ref_title:
            continue
            
        # Title ratio
        ratio = difflib.SequenceMatcher(None, ref_title, meta_title).ratio()
        
        # Boost score if year or author matches
        if meta.get("year") and meta.get("year") == parsed_ref.get("parsed_year"):
            ratio += 0.1
            
        if ratio > best_score:
            best_score = ratio
            best_match = pid
            
    # Require a decent similarity (e.g., > 0.6)
    if best_score > 0.6:
        return best_match
    return None
