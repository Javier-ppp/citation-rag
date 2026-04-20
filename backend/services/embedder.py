from sentence_transformers import SentenceTransformer
from backend.config import settings
from typing import List

# Lazy initialization
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model

def embed_text(text: str) -> List[float]:
    return get_model().encode(text).tolist()

def embed_batch(texts: List[str]) -> List[List[float]]:
    return get_model().encode(texts).tolist()
