# Citation RAG

**Local PDF Viewer with AI-Powered Citation Verification and Article Search**

Citation RAG is an innovative open-source tool that provides transparent citation tracking and evidence search for scientific PDFs—fully offline and privacy-respecting. It allows you to upload academic papers, parse their references, and rapidly verify citations using both retrieval-augmented generation (RAG) and local large language models (LLMs). All searches, metadata extraction, and citation linking are performed locally on your machine.

---

## Key Features

- **PDF Ingestion & Parsing**: Upload academic papers as PDFs. Extracts title, authors, references, and section text using PyMuPDF and intelligent parsing.
- **Smart Citation Tracking**: Hover over citation markers (e.g., [5]) in the main paper to get instant tooltips with summaries, provenance, and matching evidence passages—fully local!
- **Forward & Backward Evidence Search**:
  - **Forward**: Query a claim/statement and get the most relevant source text from your PDF database, reranked by a local LLM.
  - **Backward**: Link each citation marker in your PDF to the most likely referenced local paper, surfacing relevant text or alerting if the source PDF is missing.
- **Reference Library Management**: Visual panel to manage your uploaded main and source papers.
- **Scholarly-Minimal UI**: Modern dark-theme interface with seamless PDF.js viewing, overlays, and split-panel search.
- **Privacy-First**: No data leaves your device. All ML inference, embeddings, and vector storage uses local models/databases.
- **Fast & Extensible**: Modular Python (FastAPI) backend with clear service boundaries. Separate lightweight JS frontend.

---

## Demo

> (To do: Include screenshots or GIFs of the UI, PDF hover tooltips, evidence search in action.)

---

## How It Works

**Architecture Overview:**
- **Frontend**: PDF.js-based viewer (browser) with overlay panels for citation tooltips and forward search. All interactions via REST.
- **Backend**: FastAPI app exposing `/api/ingest`, `/api/search`, `/api/cite-check`.
- **RAG Pipeline**:
  - Ingest PDFs → Extract sections → Chunk into sentences → Embed → Store in ChromaDB (vector DB)
  - For each citation marker: match against ingested papers, retrieve relevant passages using vector similarity, rerank with local LLM (Ollama/Gemma).
  - Summarize and return evidence for seamless tooltip rendering.
- **Core Dependencies:** FastAPI, PyMuPDF, ChromaDB, sentence-transformers, Ollama (local LLM), PDF.js

For technical details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Getting Started

### 1. Requirements

- Python 3.9+
- Node.js (only for development/frontend modifications)
- Local LLM backend (supports Ollama with Gemma 4 E2B, install scording instructions [Ollama docs](https://docs.ollama.com/quickstart))
- Chrome/Firefox (for web UI)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Javier-ppp/citation-rag.git
cd citation-rag

# (Recommended) Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy and adjust the template environment file:
```bash
cp .env.example .env
# Edit .env to set model name, database path, API ports, etc.
```

### 4. Running the App

To start the backend API:
```bash
./run.sh
# Backend should be available at http://localhost:8000/
```

To launch the frontend:
- Open `http://localhost:8000/` with your browser (if backend is running, the viewer will connect automatically).

### 5. Uploading & Using Papers

1. Click "Set Main Paper" in the UI to upload the PDF you want to read/verify.
2. Optionally add any reference/source PDFs with "Add Source."
3. Hover over citation markers (e.g., [1], [5]) in the PDF to see instant verification tooltips.
4. Use the right panel’s "Forward Search" to type claims and find supporting text across your local library.
5. Or hover with your mouse over a sentence supported with a reference to see the sentences (in the referenced article) that support it. 

---

## Project Structure

```text
citation-rag/
├── backend/        # FastAPI backend (PDF parsing, embeddings, APIs)
├── frontend/       # PDF.js viewer + overlay JS app
├── test_corpus/    # Sample PDFs and test data
├── tests/          # Pytest suite: unit & integration
├── docs/           # Architecture, implementation plan, file structure
├── requirements.txt
├── run.sh
├── .env / .env.example
└── README.md
```

> See [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) for a more detailed tree.

---

## Stack

- **Python Backend**: FastAPI, PyMuPDF, ChromaDB, sentence-transformers, Pydantic, Ollama
- **Frontend**: HTML5, PDF.js, modern JS/CSS (no transpilers needed)
- **Vector DB**: ChromaDB (local, persistent)
- **LLM**: Gemma 4 E2B (via Ollama) for semantic reranking & passage summarization

---

## Test Corpus

A small open-source corpus is included in `test_corpus/` for out-of-the-box verification.

- 5 open-access PDFs are provided as sources.
- Dummy citing LaTeX document (`dummy_citing_paper.tex`/`.pdf`) for realistic demo.
- See `test_corpus/README.md` for details.

---

## Development & Contribution

1. Fork and clone the repo
2. Activate a virtual environment and install dependencies
3. Make changes in a feature branch
4. Run linting and tests: `pytest tests/`
5. Open a PR with your improvements!

Pull requests and bug reports are welcome. For larger changes, please open an issue to discuss design decisions.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

## Acknowledgements
This project was partially vibecoded using Google's Antigravity, Claude 4.6 and Geminy 3.1 

- [PDF.js](https://mozilla.github.io/pdf.js/) for document rendering.
- [sentence-transformers](https://www.sbert.net/) for embeddings.
- [Ollama](https://ollama.ai/) and the Gemma models for local LLM inference.
- [ChromaDB](https://www.trychroma.com/) for fast vector storage.

---

## Contact

Project by Javier-ppp. For questions, reach out via [GitHub Issues](https://github.com/Javier-ppp/citation-rag/issues).
