from fastapi import APIRouter, File, UploadFile, HTTPException
from backend.models import IngestResponse
from backend.services.rag_pipeline import ingest_pdf
import os
import shutil

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_route(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save temp file
    os.makedirs("backend/data/pdfs", exist_ok=True)
    temp_path = f"backend/data/pdfs/{file.filename}"
    
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        metadata = await ingest_pdf(temp_path, file.filename)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
