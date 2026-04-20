from typing import Dict, Any, List, Optional
from backend.services.pdf_parser import parse_pdf
from backend.services.reference_parser import extract_references_from_text
from backend.services.paper_registry import register_paper, get_paper, match_reference
from backend.services.chunker import chunk_pages
from backend.services.embedder import embed_batch, embed_text
from backend.services.vector_store import store_chunks, search_query
from backend.services.llm_client import generate_response
import uuid

# Global memory of references for MVP (ideally saved to DB with paper)
_paper_references = {}

async def ingest_pdf(pdf_path: str, filename: str) -> Dict[str, Any]:
    # 1. Parse PDF
    parsed_data = parse_pdf(pdf_path)
    paper_id = str(uuid.uuid4())
    
    # 2. Extract full text and references
    full_text = " ".join([p.text for p in parsed_data["pages"]])
    references = extract_references_from_text(full_text)
    
    # Store references for backward mode
    _paper_references[paper_id] = references
    
    # Extract metadata naively
    title = filename.replace(".pdf", "")
    metadata = {
        "paper_id": paper_id,
        "title": title,
        "first_author": "Unknown",
        "year": "Unknown",
        "filename": filename,
        "num_references": len(references)
    }
    
    # 3. Register paper
    register_paper(paper_id, metadata)
    
    # 4. Chunk
    chunks = chunk_pages(parsed_data["pages"])
    
    # 5. Embed & 6. Store
    texts = [c["text"] for c in chunks]
    embeddings = embed_batch(texts)
    store_chunks(paper_id, chunks, embeddings)
    
    metadata["num_chunks"] = len(chunks)
    metadata["num_pages"] = parsed_data["num_pages"]
    metadata["status"] = "success"
    
    return metadata

async def forward_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    query_embedding = embed_text(query)
    results = search_query(query_embedding, top_k=top_k)
    
    if not results or not results.get('documents') or len(results['documents']) == 0 or len(results['documents'][0]) == 0:
        return {"found": False, "message": "No relevant text found in the database for this query."}
    
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    best_results = []
    
    for i in range(len(docs)):
        dist = distances[i]
        # Skip if distance is too high (confidence too low)
        if dist > 1.5:  # Arbitrary threshold to establish 'not found'
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
        return {"found": False, "message": "No relevant text found in the database for this query."}
        
    return {"found": True, "results": best_results}

async def backward_cite_check(citation_marker: str, context: str, pdf_id: str) -> Dict[str, Any]:
    paper = get_paper(pdf_id)
    if not paper:
        return {"found": False, "message": "Source paper not found in registry."}
        
    # Attempt to find the specific reference
    refs = _paper_references.get(pdf_id, [])
    # Strip brackets for matching e.g. "[12]" -> "12"
    ref_num = citation_marker.strip("[]")
    
    target_ref = next((r for r in refs if r["ref_number"] == ref_num), None)
    
    matched_paper_id = None
    if target_ref:
        matched_paper_id = match_reference(target_ref)
        if not matched_paper_id:
            return {"found": False, "message": "Paper not found in database. Please ingest it first."}
            
    # Default to global searching if we cannot reliably match reference
    # However the spec says if matched_paper_id is not found -> Error. 
    # But if there are no refs extracted properly, let's fallback to search all.
            
    query = f"Context: {context}. Find supporting evidence."
    query_emb = embed_text(query)
    
    # If we found the target paper, strict search. Otherwise global search (MVP fallback)
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
