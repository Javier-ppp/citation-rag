# Test Corpus

This directory contains real scientific papers downloaded from arXiv for verifying the RAG pipeline.

## Ingested Papers

| File | arXiv ID | Title | Key Topic |
|------|----------|-------|-----------|
| `paper1_sam2.pdf` | 2505.07110 | SAM 2: Segment Anything in Images and Videos | Computer Vision |
| `paper2_small_lm.pdf` | 2506.02153 | Small Language Models are the Future of Agentic AI | AI Agents |
| `paper3_attention.pdf` | 1706.03762 | Attention Is All You Need | Transformers / AI |
| `paper4_trading_agents.pdf` | 2412.19437 | TradingAgents: Multi-Agents LLM Financial Trading Framework | Finance AI |
| `paper5_generic.pdf` | 2501.12345 | Sparse Multi-Modal Transformer for Alzheimer’s | Healthcare AI |

## Usage
1. Ingest these papers via the `/api/ingest` endpoint or the browser UI.
2. Use the provided `dummy_citing_paper.tex` (or its compiled PDF) to test the **Backward Citation Hover**.
3. Use the **Forward Search** to find specific cross-paper insights (e.g., "the future of agentic AI").
