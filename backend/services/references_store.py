import json
import os
from typing import Dict, List, Any

REFERENCES_PATH = "backend/data/references.json"

class ReferencesStore:
    def __init__(self):
        self._data: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        if not os.path.exists(REFERENCES_PATH):
            self._data = {}
            return
        try:
            with open(REFERENCES_PATH, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def _save(self):
        os.makedirs(os.path.dirname(REFERENCES_PATH), exist_ok=True)
        with open(REFERENCES_PATH, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

    def store_references(self, paper_id: str, references: List[Dict[str, Any]]):
        self._data[paper_id] = references
        self._save()

    def get_references(self, paper_id: str) -> List[Dict[str, Any]]:
        # Refresh from disk to ensure we have latest from other processes/restarts
        self._load()
        return self._data.get(paper_id, [])

# Global instance
refs_store = ReferencesStore()
