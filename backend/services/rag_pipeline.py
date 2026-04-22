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
        f"Structural Rules:\n"
        f"1. A paper starts with the TITLE, followed by a long list of AUTHORS, followed by the ABSTRACT.\n"
        f"2. IDENTIFY THE ANCHORS: First, find the block of many names (Authors) and the word 'Abstract' or 'Summary'.\n"
        f"3. THE TITLE is exactly the text ABOVE the authors. Include the full subtitle (e.g. text after a colon).\n"
        f"4. Ignore journal/arXiv headers at the very top (e.g. 'arXiv:2408.00714v2').\n"
        f"5. Warning: Some papers (like SAM 2) have 10-50 authors. Do not stop at the first name.\n"
        f"6. For 'first_author', return ONLY the primary first name. If not found, use the filename: {filename}\n"
        f"Text:\n{text_hint[:2000]}"
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
    try:
        logger.info(f"[CITE] Checking {citation_marker} in paper {pdf_id}")
        
        # 1. Parse citation numbers (handles [1], [1,2], [1-3] etc.)
        # Clean brackets and split by comma or dash
        inner = citation_marker.strip("[]")
        nums = []
        
        # regex to find ranges like 1-3
        range_matches = re.findall(r'(\d+)\s*[\-\u2013\u2014]\s*(\d+)', inner)
        for start, end in range_matches:
            for i in range(int(start), int(end) + 1):
                nums.append(str(i))
        
        # regex to find individual numbers not in ranges
        # (Simplified: just grab all digits and deduplicate)
        digit_matches = re.findall(r'\d+', inner)
        for d in digit_matches:
            if d not in nums:
                nums.append(d)
        
        if not nums:
            return {"found": False, "message": "No valid citation numbers found."}

        paper = get_paper(pdf_id)
        if not paper:
            return {"found": False, "message": "Main paper not found in registry."}
            
        refs = refs_store.get_references(pdf_id)
        all_results = []

        for ref_num in nums:
            target_ref = next((r for r in refs if r["ref_number"] == ref_num), None)
            if not target_ref:
                logger.warning(f"[CITE] Ref {ref_num} not found in this paper's reference list.")
                continue
                
            matched_paper_id = match_reference(target_ref)
            if not matched_paper_id:
                logger.warning(f"[CITE] Paper for Ref {ref_num} ({target_ref['parsed_title'][:20]}) not ingested.")
                all_results.append({
                    "found": False,
                    "ref_num": ref_num,
                    "title": target_ref.get("parsed_title", "Unknown"),
                    "message": "Paper not found in library."
                })
                continue

            # PERFORM SEARCH for THIS PAPER ONLY
            query = f"Context: {context}. Find supporting evidence."
            query_emb = embed_text(query)
            
            results = search_query(query_emb, top_k=4, paper_id=matched_paper_id)
            
            if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
                all_results.append({
                    "found": False,
                    "ref_num": ref_num,
                    "title": target_ref.get("parsed_title", "Unknown"),
                    "message": "No evidence found in this paper."
                })
                continue
                
            evidences = []
            
            # Evaluate the top chunks sequentially (like forward search)
            for i in range(min(3, len(results['documents'][0]))):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                
                extract_prompt = (
                    f"From the passage below, extract the 1-2 sentences that MOST DIRECTLY support "
                    f"or evidence the following claim: '{context}'.\n"
                    f"Rules:\n"
                    f"1. ONLY output the relevant sentence from the passage verbatim. No commentary, no JSON, no quotes.\n"
                    f"2. ZERO BIBLIOGRAPHY POLICY: If the passage is just a list of references, authors, or bibliography, DO NOT output anything. Return empty.\n"
                    f"3. Do not return empty placeholder text. Output EXACTLY the sentence, or nothing.\n"
                    f"Passage:\n{doc}"
                )
                
                try:
                    extracted = await generate_response(extract_prompt)
                    extracted = extracted.strip()
                    
                    # Verify the model returned something substantial and not an apology
                    if extracted and len(extracted) > 10 and not extracted.lower().startswith("no ") and not extracted.lower().startswith("i cannot"):
                        # Found a valid piece of evidence!
                        evidences.append({
                            "passage": extracted,
                            "page_num": meta['page_num'],
                            "supports": True # True because the LLM chose it as a valid support
                        })
                except Exception as e:
                    logger.error(f"[CITE] LLM extraction error on chunk {i}: {e}")

            # Emergency Fallback ONLY if all extractions failed
            if not evidences and results['documents'][0]:
                evidences.append({
                    "passage": results['documents'][0][0][:250],
                    "page_num": results['metadatas'][0][0]["page_num"],
                    "supports": False 
                })
            
            cited_paper_info = get_paper(matched_paper_id)
            
            all_results.append({
                "found": True,
                "ref_num": ref_num,
                "cited_paper": {
                    "title": cited_paper_info.get("title", "Unknown"),
                    "authors": cited_paper_info.get("first_author", "Unknown"),
                    "year": str(cited_paper_info.get("year", "Unknown"))
                },
                "evidences": evidences,
                "confidence": 1.0 / (1.0 + results['distances'][0][0])
            })

        if not all_results:
            return {"found": False, "message": "No citations matched your library."}
            
        return {
            "found": True, 
            "is_multi": len(all_results) > 1,
            "results": all_results
        }
    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        logger.error(f"Global crash in backward_cite_check: {err_msg}")
        return {"found": False, "message": f"Backend Crash: {str(exc)}"}


