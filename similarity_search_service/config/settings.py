"""
Configuration Settings
======================
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=1)
    api_timeout: int = Field(default=300)
    
    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_ssl: bool = Field(default=False)
    redis_max_connections: int = Field(default=50)
    redis_socket_timeout: int = Field(default=5)
    
    # Azure Storage Configuration
    azure_storage_connection_string: str
    azure_table_name: str = Field(default="fhekvstore")
    azure_timeout: int = Field(default=30)
    
    # FHE Configuration - Base64 Keys
    tenseal_full_context_base64: Optional[str] = Field(default=None)
    
    # FHE Parameters
    fhe_poly_modulus_degree: int = Field(default=4096)
    fhe_plain_modulus: int = Field(default=1032193)
    
    # Search Configuration
    max_candidates: int = Field(default=200)
    default_top_k: int = Field(default=5)
    max_top_k: int = Field(default=50)
    
    # Decryption Service
    decryption_service_url: Optional[str] = Field(default="http://localhost:9000/api/decrypt")
    decryption_service_api_key: Optional[str] = Field(default=None)
    
    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="text")
    enable_performance_logging: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
