from fastapi import APIRouter
from typing import List, Dict, Any
from backend.services.paper_registry import _load_registry

router = APIRouter()

@router.get("/papers", response_model=List[Dict[str, Any]])
async def get_all_papers():
    registry = _load_registry()
    papers = []
    for pid, meta in registry.items():
        # Provide default role for legacy papers
        if "role" not in meta:
            meta["role"] = "source"
        papers.append(meta)
    return papers
