import logging
import uuid
import os
from typing import Dict, Any, List, Optional
from backend.services.pdf_parser import parse_pdf
from backend.services.reference_parser import extract_references_llm, extract_references_from_text
from backend.services.paper_registry import register_paper, get_paper, match_reference, _load_registry, REGISTRY_PATH
from backend.services.chunker import chunk_pages
from backend.services.embedder import embed_batch, embed_text
from backend.services.vector_store import store_chunks, search_query, get_collection, reset_vector_db
from backend.services.llm_client import generate_response
from backend.services.references_store import refs_store, REFERENCES_PATH
import shutil
import json
import re

async def clear_all_data() -> bool:
    """Wipes all persistent data to start a fresh session."""
    logger.info("[SESSION] Starting complete data reset...")
    try:
        # 1. Reset Vector DB
        db_reset = reset_vector_db()
        if not db_reset:
            logger.warning("[SESSION] Vector DB reset reported failure, continuing...")
        
        # 2. Clear Registry logic
        if os.path.exists(REGISTRY_PATH):
            os.remove(REGISTRY_PATH)
            logger.info(f"[SESSION] Deleted registry at {REGISTRY_PATH}")
            
        # 3. Clear References
        if os.path.exists(REFERENCES_PATH):
            os.remove(REFERENCES_PATH)
            logger.info(f"[SESSION] Deleted references at {REFERENCES_PATH}")
            
        # 4. Delete PDF files
        pdf_dir = "backend/data/pdfs"
        if os.path.exists(pdf_dir):
            for filename in os.listdir(pdf_dir):
                file_path = os.path.join(pdf_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"[SESSION] Could not delete {file_path}: {e}")
            logger.info(f"[SESSION] Cleared PDF directory {pdf_dir}")
                    
        return True
    except Exception as e:
        logger.error(f"[SESSION] Critical failure during clear data: {e}")
        return False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def extract_metadata(text_hint: str, filename: str) -> Dict[str, str]:
    """Uses LLM to extract clean metadata from the first page text."""
    prompt = (
        f"Extract bibliographic metadata from the following PDF start text.\n"
        f"Return ONLY a JSON object with keys: 'title', 'first_author', 'year'.\n"
        f"If you cannot find a field, use the filename hint: {filename}\n"
        f"Text: {text_hint[:2000]}"
    )
    
    try:
        response = await generate_response(prompt)
        # Find JSON block in response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return {
                "title": data.get("title", filename.replace(".pdf", "")),
                "first_author": data.get("first_author", "Unknown"),
                "year": str(data.get("year", "2026"))
            }
    except Exception as e:
        logger.warning(f"[METADATA] LLM extraction failed: {e}")
        
    return {
        "title": filename.replace(".pdf", ""),
        "first_author": "Unknown",
        "year": "2026"
    }

async def ingest_pdf(pdf_path: str, filename: str, role: str = "source") -> Dict[str, Any]:
    logger.info(f"[INGEST] Starting: {filename} as {role}")
    
    # 1. Deduplication check
    registry = _load_registry()
    existing_pid = next((pid for pid, meta in registry.items() if meta.get("filename") == filename), None)
    
    if existing_pid:
        logger.info(f"[INGEST] Existing paper found ({existing_pid}). Cleaning old vectors...")
        try:
            collection = get_collection()
            collection.delete(where={"paper_id": existing_pid})
        except Exception as e:
            logger.warning(f"[INGEST] Cleanup of old vectors failed: {e}")
        paper_id = existing_pid
    else:
        paper_id = str(uuid.uuid4())
        
    # 2. Parse PDF
    parsed_data = parse_pdf(pdf_path)
    
    # 3. Extract references
    full_text = " ".join([p.text for p in parsed_data["pages"]])
    
    if role == "main":
        logger.info("[INGEST] Using LLM for reference extraction...")
        references = await extract_references_llm(full_text)
    else:
        references = extract_references_from_text(full_text)
    
    # Only store references if it's the main paper (efficiency)
    refs_store.store_references(paper_id, references)
    logger.info(f"[INGEST] Detected {len(references)} references.")
    
    # Extract metadata using AI
    metadata_hint = parsed_data.get("metadata_hint", "")
    ai_meta = await extract_metadata(metadata_hint, filename)
    
    metadata = {
        "paper_id": paper_id,
        "title": ai_meta["title"],
        "first_author": ai_meta["first_author"],
        "year": ai_meta["year"],
        "filename": filename,
        "num_references": len(references),
        "role": role
    }
    
    # 4. Register paper (this handles demoting previous main)
    register_paper(paper_id, metadata)
    
    # 5. Chunk
    chunks = chunk_pages(parsed_data["pages"])
    logger.info(f"[INGEST] Splitting into {len(chunks)} chunks...")
    
    # 6. Embed & 7. Store
    texts = [c["text"] for c in chunks]
    embeddings = embed_batch(texts)
    store_chunks(paper_id, chunks, embeddings)
    
    metadata["num_chunks"] = len(chunks)
    metadata["num_pages"] = parsed_data["num_pages"]
    metadata["status"] = "success"
    
    logger.info(f"[INGEST] Completed: {paper_id} ({role})")
    return metadata

async def forward_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    logger.info(f"[SEARCH] Query: '{query}' (Sources Only)")
    query_embedding = embed_text(query)
    
    # Filter to only search across papers flagged as 'source'
    from backend.services.paper_registry import get_source_paper_ids
    source_ids = get_source_paper_ids()
    
    if not source_ids:
        logger.info("[SEARCH] No source papers available.")
        return {"found": False, "message": "No source papers available to search. Please ingest some first."}

    # ChromaDB 'where' filter with '$in' for multiple paper_ids
    results = search_query(query_embedding, top_k=top_k, paper_id={"$in": source_ids} if len(source_ids) > 1 else source_ids[0])
    
    if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
        logger.info("[SEARCH] No matches found in source papers.")
        return {"found": False, "message": "No relevant text found in the source papers."}
    
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    logger.info(f"[SEARCH] Found {len(docs)} matches. Top distance: {distances[0]:.4f}")
    
    best_results = []
    
    for i in range(len(docs)):
        dist = distances[i]
        if dist > 1.8:
            continue
            
        paper_id = metadatas[i]["paper_id"]
        paper_info = get_paper(paper_id)
        full_chunk = docs[i]
        
        # Step 1: Extract the most relevant 1-3 sentences (citation-sized snippet)
        extract_prompt = (
            f"From the passage below, extract the 1-3 sentences that MOST DIRECTLY support "
            f"or evidence the following claim: '{query}'.\n"
            f"Rules: ONLY output the reelevant sentece in the passage verbatim. No commentary, no ellipsis, no quotes.\n"
            f"Passage: {full_chunk}"
        )
        extracted = await generate_response(extract_prompt)
        
        # Step 2: Brief relevance explanation  
        explain_prompt = (
            f"In one sentence, explain WHY this passage is relevant to: '{query}'.\n"
            f"Passage: {extracted or full_chunk}"
        )
        explanation = await generate_response(explain_prompt)
        
        best_results.append({
            "passage": extracted.strip() if extracted else full_chunk,
            "full_chunk": full_chunk,
            "source_pdf": paper_info.get("filename") if paper_info else "Unknown",
            "title": paper_info.get("title") if paper_info else "Unknown",
            "first_author": paper_info.get("first_author") if paper_info else "Unknown",
            "page_num": metadatas[i]["page_num"],
            "relevance_score": 1.0 / (1.0 + dist),
            "llm_explanation": explanation
        })
    
    if len(best_results) == 0:
        return {"found": False, "message": "Results found but confidence too low."}
        
    return {"found": True, "results": best_results}

async def backward_cite_check(citation_marker: str, context: str, pdf_id: str) -> Dict[str, Any]:
    logger.info(f"[CITE] Checking {citation_marker} in paper {pdf_id}")
    paper = get_paper(pdf_id)
    if not paper:
        return {"found": False, "message": "Source paper not found in registry."}
        
    refs = refs_store.get_references(pdf_id)
    ref_num = citation_marker.strip("[]")
    
    target_ref = next((r for r in refs if r["ref_number"] == ref_num), None)
    
    matched_paper_id = None
    if target_ref:
        logger.info(f"[CITE] Found reference entry: {target_ref['parsed_title'][:30]}...")
        matched_paper_id = match_reference(target_ref)
        if not matched_paper_id:
            logger.warning("[CITE] Cited paper metadata found but paper not in database.")
            return {"found": False, "message": "Cited paper not found in the 'Source' database. Please ingest it first."}
    else:
        logger.warning(f"[CITE] Reference marker {citation_marker} not found in paper's reference list.")
        return {"found": False, "message": "Citation marker not found in reference list."}
            
    query = f"Context: {context}. Find supporting evidence."
    query_emb = embed_text(query)
    
    # matched_paper_id is verified to be a 'source' paper in match_reference
    results = search_query(query_emb, top_k=3, paper_id=matched_paper_id)
    
    if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
        return {"found": False, "message": "No supporting evidence found in the cited source."}
        
    best_doc = results['documents'][0][0]
    best_meta = results['metadatas'][0][0]
    
    prompt = f"Extract the most relevant 1-2 sentences from this passage that clearly support the claim: '{context}'.\nPassage: {best_doc}"
    extracted = await generate_response(prompt)
    
    cited_paper_info = get_paper(best_meta["paper_id"])
    
    return {
        "found": True,
        "cited_paper": {
            "title": cited_paper_info.get("title") if cited_paper_info else "Unknown",
            "authors": cited_paper_info.get("first_author") if cited_paper_info else "Unknown",
            "year": cited_paper_info.get("year") if cited_paper_info else "Unknown"
        },
        "best_passage": extracted if extracted else best_doc,
        "page_num": best_meta["page_num"],
        "confidence": 1.0 / (1.0 + results['distances'][0][0])
    }


