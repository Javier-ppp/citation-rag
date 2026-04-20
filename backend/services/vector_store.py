import chromadb
from typing import List, Dict, Any, Optional
from backend.config import settings
import os

_client = None

def get_client():
    global _client
    if _client is None:
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        # Using persistent client allows saving DB locally
        _client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    return _client

def get_collection():
    return get_client().get_or_create_collection(name="papers")

def store_chunks(paper_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
    """
    Stores chunks and their respective embeddings to ChromaDB.
    Expected chunk format: {"text": str, "page_num": int, "chunk_idx": int}
    """
    collection = get_collection()
    
    ids = [f"{paper_id}_chunk_{c['chunk_idx']}" for c in chunks]
    metadatas = [
        {
            "paper_id": paper_id,
            "page_num": c["page_num"],
            "chunk_idx": c["chunk_idx"]
        } for c in chunks
    ]
    texts = [c["text"] for c in chunks]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts
    )

def search_query(query_embedding: List[float], top_k: int = 5, paper_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Search ChromaDB for chunks closest to the given query_embedding.
    If paper_id is provided, filters the search strictly to that paper's chunks.
    """
    collection = get_collection()
    
    where_filter = {"paper_id": paper_id} if paper_id else None
    
    # query returns a dict with 'ids', 'distances', 'metadatas', 'documents'
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )
    
    return results
