from fastapi import APIRouter
from backend.models import CiteCheckRequest, CiteCheckResponse
from backend.services.rag_pipeline import backward_cite_check

router = APIRouter()

@router.post("/cite-check", response_model=CiteCheckResponse)
async def cite_route(req: CiteCheckRequest):
    results = await backward_cite_check(req.citation_marker, req.context, req.pdf_id)
    return results
