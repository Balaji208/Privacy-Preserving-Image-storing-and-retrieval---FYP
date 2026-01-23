from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = "encrypted-images"  # ← NEW
    
    # BFV Context
    BFV_CONTEXT_PATH: str = "bfv_keys/bfv_context_public.bin"
    
    # Performance
    MAX_CANDIDATES: int = 200
    TOP_K_DEFAULT: int = 10
    ENABLE_PARALLEL_RANKING: bool = True
    NUM_THREADS: int = 8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
