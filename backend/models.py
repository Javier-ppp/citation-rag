from pydantic import BaseModel
from typing import List, Optional

# --- Ingest Models ---

class Citation(BaseModel):
    marker: str
    position: int

class Page(BaseModel):
    page_num: int
    text: str
    citations: List[Citation] = []

class IngestResponse(BaseModel):
    paper_id: str
    title: Optional[str]
    first_author: Optional[str]
    year: Optional[str]
    num_pages: int
    num_chunks: int
    num_references: int
    role: str
    status: str

# --- Search Models (Forward Mode) ---

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    passage: str
    source_pdf: str
    title: Optional[str]
    first_author: Optional[str]
    page_num: int
    relevance_score: float
    llm_explanation: Optional[str]

class SearchResponse(BaseModel):
    found: bool
    results: List[SearchResult] = []
    message: Optional[str] = None

# --- Cite Models (Backward Mode) ---

class CiteCheckRequest(BaseModel):
    citation_marker: str
    context: str
    pdf_id: str

class CitedPaperInfo(BaseModel):
    title: Optional[str]
    authors: Optional[str]
    year: Optional[str]

class CiteEvidence(BaseModel):
    passage: str
    page_num: int
    supports: bool

class CiteItem(BaseModel):
    found: bool
    ref_num: str
    cited_paper: Optional[CitedPaperInfo] = None
    evidences: List[CiteEvidence] = []
    confidence: Optional[float] = None
    message: Optional[str] = None

class CiteCheckResponse(BaseModel):
    found: bool
    is_multi: bool = False
    results: List[CiteItem] = []
    message: Optional[str] = None
