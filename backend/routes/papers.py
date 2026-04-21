from fastapi import APIRouter
from typing import List, Dict, Any
from backend.services.paper_registry import _load_registry, match_reference
from backend.services.references_store import refs_store

router = APIRouter()

@router.get("/papers", response_model=List[Dict[str, Any]])
async def get_all_papers():
    registry = _load_registry()
    papers = []
    
    # 1. Identify the Main paper
    main_paper = None
    main_pid = None
    for pid, meta in registry.items():
        if meta.get("role") == "main":
            main_paper = meta
            main_pid = pid
            break

    # To track which source papers have been linked to a citation
    matched_source_ids = set()

    if main_paper:
        papers.append(main_paper)
        
        # 2. Get parsed references from the store
        refs = refs_store.get_references(main_pid)
        
        # 3. Match each reference sequentially
        for ref in refs:
            matched_pid = match_reference(ref)
            ref_num = ref.get("ref_number")
            
            if matched_pid and matched_pid in registry:
                # Reference is satisfied by an uploaded source
                meta = dict(registry[matched_pid])
                meta["role"] = "source"
                meta["status"] = "linked"
                meta["ref_number"] = ref_num
                papers.append(meta)
                matched_source_ids.add(matched_pid)
            else:
                # Reference missing: inject placeholder
                title = ref.get("parsed_title") or ref.get("raw_text") or "Unknown Title"
                papers.append({
                    "paper_id": f"missing-{ref_num}",
                    "title": f"[Missing] {title}",
                    "filename": "Not provided",
                    "role": "source",
                    "status": "missing",
                    "ref_number": ref_num
                })

    # 4. Append remaining source papers that couldn't be linked to any citation
    for pid, meta in registry.items():
        # Handle legacy roles
        if "role" not in meta:
            meta["role"] = "source"
            
        if meta.get("role") != "main" and pid not in matched_source_ids:
            meta_copy = dict(meta)
            meta_copy["status"] = "unlinked"
            papers.append(meta_copy)
            
    # For edge cases where no main paper exists
    if not main_paper:
        # Loop 4 already handled unlinked sources, and if there's no main_paper,
        # matched_source_ids is empty, so they are already in the list.
        # We don't need this second loop.
        pass

    return papers
