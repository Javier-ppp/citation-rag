from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_API_URL: str = "http://localhost:11434"
    LLM_MODEL_NAME: str = "gemma2:2b"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CHROMA_DB_PATH: str = "./backend/data/chroma_db"
    CHUNK_SIZE_TOKENS: int = 500
    API_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    class Config:
        env_file = ".env"

settings = Settings()
