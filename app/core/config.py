from pydantic import BaseModel
import os

class Settings(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
    OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")

    VECTOR_INDEX_PATH: str = os.getenv("VECTOR_INDEX_PATH", "data/index/faiss.index")
    VECTOR_META_PATH: str = os.getenv("VECTOR_META_PATH", "data/index/meta.json")

    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "6"))
    MAX_POLICY_CHUNK_CHARS: int = int(os.getenv("MAX_POLICY_CHUNK_CHARS", "2400"))

settings = Settings()
