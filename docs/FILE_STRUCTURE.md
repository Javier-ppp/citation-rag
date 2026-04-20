# Project File Structure

```text
citation-rag/
├── .env                          # Config (model name, ports, paths)
├── .env.example                  # Template for .env (committed to git)
├── .gitignore
├── requirements.txt              # Python dependencies
├── README.md
│
├── docs/
│   ├── ARCHITECTURE.md           # System architecture diagram + ADRs
│   ├── FILE_STRUCTURE.md         # This file structure reference
│   └── PLAN.md                   # Full Implementation Plan
│
├── backend/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, CORS, static files
│   ├── config.py                 # Settings from .env (Pydantic BaseSettings)
│   ├── models.py                 # Pydantic request/response schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py         # PyMuPDF text extraction + citation detection
│   │   ├── reference_parser.py   # Parse reference list from paper (IEEE style)
│   │   ├── paper_registry.py     # JSON registry: paper metadata + matching
│   │   ├── chunker.py            # Sentence-level chunking logic
│   │   ├── embedder.py           # sentence-transformers wrapper
│   │   ├── vector_store.py       # ChromaDB operations (add, query, filter by paper_id)
│   │   ├── llm_client.py         # Ollama HTTP API wrapper
│   │   └── rag_pipeline.py       # Orchestrates: ingest / forward / backward flows
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ingest.py             # POST /api/ingest (upload PDF)
│   │   ├── search.py             # POST /api/search (forward mode)
│   │   └── cite.py               # POST /api/cite-check (backward mode)
│   │
│   └── data/                     # Local storage (gitignored)
│       ├── pdfs/                 # Uploaded PDFs
│       ├── chroma_db/            # ChromaDB persistent storage
│       └── paper_registry.json   # Metadata of all ingested papers
│
├── frontend/
│   ├── index.html                # Main page: PDF viewer + panels
│   ├── css/
│   │   └── style.css             # All styles (scholarly-minimal dark theme)
│   ├── js/
│   │   ├── app.js                # Main app logic, state management
│   │   ├── pdf-viewer.js         # pdf.js integration + page rendering
│   │   ├── citation-overlay.js   # Hover detection + tooltip rendering
│   │   ├── forward-search.js     # Forward mode panel logic
│   │   └── api-client.js         # Fetch wrappers for backend API
│   └── lib/
│       └── pdf.min.js            # pdf.js library (vendored)
│
├── test_corpus/                  # Dummy test data (committed)
│   ├── papers/                   # 5 open-access PDFs
│   ├── dummy_citing_paper.tex    # LaTeX doc that cites the 5 papers
│   ├── dummy_citing_paper.pdf    # Compiled version
│   └── README.md                 # Explains what each paper is
│
└── tests/
    ├── __init__.py
    ├── conftest.py               # Shared fixtures (sample PDFs, test ChromaDB)
    ├── test_pdf_parser.py        # Unit: text extraction + citation regex
    ├── test_reference_parser.py  # Unit: reference list parsing
    ├── test_paper_registry.py    # Unit: paper metadata matching
    ├── test_chunker.py           # Unit: sentence boundary chunking
    ├── test_rag_pipeline.py      # Integration: full ingest → query flow
    └── test_api.py               # Integration: FastAPI endpoint tests
```
