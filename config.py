from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "LaTeX Compilation Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_POOL_SIZE: int = 20
    
    # Compiler Configuration
    MAX_COMPILER_WORKERS: int = 4
    COMPILATION_TIMEOUT: int = 30
    OUTPUT_DIR: str = "pdf_output"
    
    # File Management
    CLEANUP_THRESHOLD: int = 1000
    FILE_RETENTION_DAYS: int = 7
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()