from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Union, Any
from datetime import datetime

class LatexRequest(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="LaTeX content to be compiled"
    )
    template_id: Optional[str] = Field(
        None,
        description="Optional template ID to use for compilation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "\\documentclass{article}\\begin{document}Hello World\\end{document}",
                "template_id": None
            }
        }

class DocumentResult(BaseModel):
    url: str = Field(
        ...,
        description="Presigned URL for accessing the compiled PDF"
    )
    key: str = Field(
        ...,
        description="S3 key for the compiled document"
    )
    expires_in: int = Field(
        default=3600,
        description="Time in seconds until the presigned URL expires"
    )

class ErrorResult(BaseModel):
    error: str = Field(
        ...,
        description="Error message describing what went wrong"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details if available"
    )

class LatexResponse(BaseModel):
    status: str = Field(
        ...,
        description="Status of the compilation (success/error)"
    )
    result: Union[DocumentResult, ErrorResult] = Field(
        ...,
        description="Either successful document information or error details"
    )
    job_id: str = Field(
        ...,
        description="Unique identifier for the compilation job"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of when the response was created"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "result": {
                    "url": "https://your-bucket.s3.region.amazonaws.com/pdfs/user123/123e4567.pdf",
                    "key": "cvs/user123/123e4567.pdf",
                    "expires_in": 3600
                },
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-12-19T10:00:00.000Z"
            }
        }

class HealthCheck(BaseModel):
    status: str = Field(
        ...,
        description="Overall health status of the service"
    )
    timestamp: datetime = Field(
        ...,
        description="Current timestamp of the health check"
    )
    version: str = Field(
        ...,
        description="Version of the service"
    )
    active_workers: int = Field(
        ...,
        description="Number of active compiler workers"
    )
    storage_status: str = Field(
        ...,
        description="Status of the S3 storage connection"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if any component is unhealthy"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-12-19T10:00:00.000Z",
                "version": "1.0.0",
                "active_workers": 4,
                "storage_status": "healthy",
                "error": None
            }
        }