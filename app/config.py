# app/config.py
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache
import json

class Settings(BaseSettings):
    PROJECT_NAME: str
    VERSION: str
    API_V1_STR: str
    HOST: str
    PORT: int
    WORKERS: int
    DEBUG: bool
    REDIS_URL: str
    REDIS_POOL_SIZE: int
    MAX_COMPILER_WORKERS: int
    COMPILATION_TIMEOUT: int
    OUTPUT_DIR: str
    CLEANUP_THRESHOLD: int
    FILE_RETENTION_DAYS: int
    RATE_LIMIT_PER_MINUTE: int
    CORS_ORIGINS: List[str]
    ALLOWED_HOSTS: List[str]
    LOG_LEVEL: str
    JSON_LOGS: bool
    ENABLE_METRICS: bool

    class Config:
        env_file = ".env"
        case_sensitive = True

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name in ["CORS_ORIGINS", "ALLOWED_HOSTS"]:
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return [raw_val]
            return raw_val

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()