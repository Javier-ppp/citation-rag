from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
import uvicorn

app = FastAPI(title="Citation RAG API")

# Setup CORS middleware
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Citation RAG API is running"}

from backend.routes import ingest, search, cite, papers

app.include_router(ingest.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(cite.router, prefix="/api")
app.include_router(papers.router, prefix="/api")

# Serve the frontend statically AFTER API routes
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.API_PORT, reload=True)
