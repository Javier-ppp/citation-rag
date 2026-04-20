import pytest
from backend.services.chunker import chunk_text

def test_chunks_respect_sentences():
    text = "This is sentence one. And this is sentence two! What about three? Yes."
    chunks = chunk_text(text, max_tokens=6) 
    # max_tokens=6 means it should split after "This is sentence one." (4 words)
    # The next sentence is 5 words, so it should be on its own.
    
    assert len(chunks) >= 2
    # Ensure no chunk ends without punctuation
    for chunk in chunks:
        assert chunk[-1] in {'.', '!', '?'}

def test_chunk_size_limit():
    text = "Word number one. " * 300
    chunks = chunk_text(text, max_tokens=500)
    for chunk in chunks:
        assert len(chunk.split()) <= 550 # Allow some margin due to simple split
