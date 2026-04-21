from fastapi import APIRouter, HTTPException
from backend.services.rag_pipeline import clear_all_data

router = APIRouter()

@router.post("/reset")
async def reset_session():
    """Resets the entire RAG session (deletes all papers)."""
    success = await clear_all_data()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset session")
    return {"message": "Session reset successfully"}
