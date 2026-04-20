import httpx
from backend.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def generate_response(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
    url = f"{settings.OLLAMA_API_URL}/api/generate"
    payload = {
        "model": settings.LLM_MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    if system_prompt:
        payload["system"] = system_prompt
        
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response")
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return None
