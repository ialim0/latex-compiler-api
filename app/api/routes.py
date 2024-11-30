# app/api/routes.py

from fastapi import APIRouter, Depends
from app.models.schemas import LatexRequest, LatexResponse, HealthCheck
from app.services.latex_compiler import LatexCompiler
from app.config import settings
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.post("/compile", response_model=LatexResponse)
async def compile_latex(
    request: LatexRequest,
    compiler: LatexCompiler = Depends()
):
    job_id = str(uuid.uuid4())
    success, result = await compiler.compile_latex(request.content, job_id)
    
    if success:
        pdf_url = f"/pdf/{result}"
        return LatexResponse(
            status="success",
            result=pdf_url,
            job_id=job_id,
            created_at=datetime.now(timezone.utc)
        )
    else:
        return LatexResponse(
            status="error",
            result={"error": result},
            job_id=job_id,
            created_at=datetime.now(timezone.utc)
        )

@router.get("/health", response_model=HealthCheck)
async def health_check():
    compiler = LatexCompiler() 
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        active_workers=compiler.active_workers  
    )
