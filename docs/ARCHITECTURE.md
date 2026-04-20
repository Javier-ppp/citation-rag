# Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (localhost:8000)              │
│  ┌───────────────────────────────────────────────────┐  │
│  │              pdf.js Viewer + Overlay               │  │
│  │  ┌─────────────┐  ┌────────────────────────────┐  │  │
│  │  │  PDF Canvas  │  │  Citation Tooltip Overlay  │  │  │
│  │  └─────────────┘  └────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Forward Search Panel (paste → find source) │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                          │ HTTP/REST                    │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ /api/ingest│  │/api/search   │  │/api/cite-check │  │
│  │ (upload &  │  │(forward mode)│  │(backward mode) │  │
│  │  index PDF)│  │              │  │                │  │
│  └─────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│        │                │                   │           │
│  ┌─────▼────────────────▼───────────────────▼────────┐  │
│  │              RAG Service Layer                     │  │
│  │  PyMuPDF → Chunk → Embed → Store/Retrieve         │  │
│  └──────┬────────────────────┬───────────────────────┘  │
│         │                    │                          │
│  ┌──────▼──────┐   ┌────────▼────────┐                 │
│  │  ChromaDB   │   │  Ollama (LLM)   │                 │
│  │  (vectors + │   │  Gemma 4 E2B    │                 │
│  │  metadata)  │   │  (rerank +      │                 │
│  │             │   │   summarize)    │                 │
│  └─────────────┘   └─────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

1. **INGEST:**
   * PDF → PyMuPDF text → extract paper metadata (title, authors, journal)
   * parse reference list → sentence chunks → embed → ChromaDB
   * store metadata: {paper_id, title, authors, journal, page, chunk_idx}

2. **FORWARD:**
   * statement → embed → ChromaDB top-k → LLM rerank → best passage + source
   * if no passage above confidence threshold → "No relevant text found"

3. **BACKWARD:**
   * citation [N] in Paper A
   * parse Paper A's reference list → find reference [N]
   * match reference to ingested paper (by title/authors)
   * if not found → "Paper not found. Please ingest it."
   * if found → ChromaDB search ONLY that paper's chunks
   * LLM extract most relevant passage → tooltip
