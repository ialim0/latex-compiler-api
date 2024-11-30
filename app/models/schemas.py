#app/models/schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union
from datetime import datetime

class LatexRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    template_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "\\documentclass{article}\\begin{document}Hello World\\end{document}",
                "template_id": None
            }
        }

class LatexResponse(BaseModel):
    status: str
    result: Union[str, Dict[str, str]]
    job_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str
    active_workers: int