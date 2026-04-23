import nltk
from typing import List, Dict, Any

# Ensure we have the punkt tokenizer
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

def chunk_text(text: str, max_tokens: int = 80) -> List[str]:
    """
    Splits text into chunks of maximum `max_tokens` (approximated by words),
    respecting sentence boundaries. Default 80 words ≈ 4-5 sentences for
    precise citation-level retrieval.
    """
    sentences = nltk.tokenize.sent_tokenize(text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        # Simple word count as token approx
        sentence_length = len(sentence.split())
        
        if current_length + sentence_length > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
        else:
            current_chunk.append(sentence)
            current_length += sentence_length
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def chunk_pages(pages: List[Any], max_tokens: int = 80) -> List[Dict[str, Any]]:
    """
    Takes a list of Page objects and chunks them, returning a list of chunk dicts including metadata.
    Automatically truncates the document at the 'References' or 'Bibliography' section to 
    prevent noise from entering the vector database.
    """
    import re
    all_chunks = []
    chunk_idx = 0
    
    for page in pages:
        # Heuristic: Find reference sections only in the latter half of the document
        if page.page_num > len(pages) * 0.5:
            # Look for headers like "References", "REFERENCES", "Bibliography" bordered by newlines
            ref_match = re.search(r'\n(?:\d{1,2}\.?\s*)?(References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*\n', page.text)
            if ref_match:
                # Truncate to everything before the bibliography header
                page.text = page.text[:ref_match.start()]
                
        text_chunks = chunk_text(page.text, max_tokens)
        for t_chunk in text_chunks:
            # We don't want empty chunks
            if not t_chunk.strip():
                continue
            all_chunks.append({
                "page_num": page.page_num,
                "chunk_idx": chunk_idx,
                "text": t_chunk
            })
            chunk_idx += 1
            
        # If we truncated the text on this page because of a bibliography match, 
        # stop processing all subsequent pages entirely (avoids indexing multi-page bibliographies).
        if page.page_num > len(pages) * 0.5 and ref_match:
            break
            
    return all_chunks
