from fastapi import APIRouter
from backend.models import SearchRequest, SearchResponse
from backend.services.rag_pipeline import forward_search

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_route(req: SearchRequest):
    results = await forward_search(req.query, req.top_k)
    return results
