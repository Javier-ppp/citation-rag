import logging
import uuid
import os
from typing import Dict, Any, List, Optional
from backend.services.pdf_parser import parse_pdf
from backend.services.reference_parser import extract_references_from_text
from backend.services.paper_registry import register_paper, get_paper, match_reference, _load_registry
from backend.services.chunker import chunk_pages
from backend.services.embedder import embed_batch, embed_text
from backend.services.vector_store import store_chunks, search_query, get_collection
from backend.services.llm_client import generate_response
from backend.services.references_store import refs_store

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def ingest_pdf(pdf_path: str, filename: str) -> Dict[str, Any]:
    logger.info(f"[INGEST] Starting: {filename}")
    
    # 1. Deduplication check
    registry = _load_registry()
    existing_pid = next((pid for pid, meta in registry.items() if meta.get("filename") == filename), None)
    
    if existing_pid:
        logger.info(f"[INGEST] Existing paper found ({existing_pid}). Cleaning old vectors...")
        try:
            collection = get_collection()
            # Simple metadata-based delete if supported by ChromaDB version
            collection.delete(where={"paper_id": existing_pid})
        except Exception as e:
            logger.warning(f"[INGEST] Cleanup of old vectors failed: {e}")
        paper_id = existing_pid
    else:
        paper_id = str(uuid.uuid4())
        
    # 2. Parse PDF
    parsed_data = parse_pdf(pdf_path)
    
    # 3. Extract full text and references
    full_text = " ".join([p.text for p in parsed_data["pages"]])
    references = extract_references_from_text(full_text)
    
    # Store references persistently
    refs_store.store_references(paper_id, references)
    logger.info(f"[INGEST] Detected {len(references)} references.")
    
    # Extract metadata
    metadata = {
        "paper_id": paper_id,
        "title": filename.replace(".pdf", ""),
        "first_author": "Multiple" if len(parsed_data["pages"]) > 0 else "Unknown",
        "year": "2026",
        "filename": filename,
        "num_references": len(references)
    }
    
    # 4. Register paper
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
    
    logger.info(f"[INGEST] Completed: {paper_id}")
    return metadata

async def forward_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    logger.info(f"[SEARCH] Query: '{query}'")
    query_embedding = embed_text(query)
    results = search_query(query_embedding, top_k=top_k)
    
    if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
        logger.info("[SEARCH] No matches found.")
        return {"found": False, "message": "No relevant text found in the database for this query."}
    
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    logger.info(f"[SEARCH] Found {len(docs)} matches. Top distance: {distances[0]:.4f}")
    
    best_results = []
    
    for i in range(len(docs)):
        dist = distances[i]
        # Skip if distance is too high
        if dist > 1.8:  # Slightly loosened threshold
            continue
            
        paper_id = metadatas[i]["paper_id"]
        paper_info = get_paper(paper_id)
        
        prompt = f"Does the following passage support or relate to the statement: '{query}'?\nPassage: {docs[i]}\nExplain briefly."
        explanation = await generate_response(prompt)
        
        best_results.append({
            "passage": docs[i],
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
        
    # Attempt to find the specific reference from persistent store
    refs = refs_store.get_references(pdf_id)
    ref_num = citation_marker.strip("[]")
    
    target_ref = next((r for r in refs if r["ref_number"] == ref_num), None)
    
    matched_paper_id = None
    if target_ref:
        logger.info(f"[CITE] Found reference entry: {target_ref['parsed_title'][:30]}...")
        matched_paper_id = match_reference(target_ref)
        if not matched_paper_id:
            logger.warning("[CITE] Cited paper metadata found but paper not in database.")
            return {"found": False, "message": "Paper not found in database. Please ingest it first."}
    else:
        logger.warning(f"[CITE] Reference marker {citation_marker} not found in paper's reference list.")
            
    query = f"Context: {context}. Find supporting evidence."
    query_emb = embed_text(query)
    
    results = search_query(query_emb, top_k=3, paper_id=matched_paper_id)
    
    if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
        return {"found": False, "message": "No supporting evidence found."}
        
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

