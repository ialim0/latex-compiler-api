# app/models/shema.py

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Union
from datetime import datetime, timezone

class LatexRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    template_id: Optional[str] = None

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty or whitespace')
        return v

    class Config:
        schema_extra = {
            "example": {
                "content": "\\documentclass{article}\\begin{document}Hello World\\end{document}",
                "template_id": None
            }
        }

class LatexResponse(BaseModel):
    status: str = Field(..., description="Status of the compilation process")
    result: Union[str, Dict[str, str]] = Field(
        ...,
        description="Result of the compilation; could be a filename or error message"
    )
    job_id: str = Field(..., description="Unique identifier for the compilation job")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "result": "123e4567-e89b-12d3-a456-426614174000.pdf",
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2023-09-14T12:34:56.789Z"
            }
        }

class HealthCheck(BaseModel):
    status: str = Field(..., description="Overall status of the service")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field(..., description="Current version of the service")
    active_workers: int = Field(..., description="Number of active worker processes")

    class Config:
        schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2023-09-14T12:34:56.789Z",
                "version": "1.0.0",
                "active_workers": 4
            }
        }
