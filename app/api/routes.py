from fastapi import APIRouter, BackgroundTasks, Depends
from app.models.schemas import LatexRequest, LatexResponse, HealthCheck
from app.services.latex_compiler import LatexCompiler
from app.config import get_settings
import uuid
from datetime import datetime

router = APIRouter()
settings = get_settings()

@router.post("/compile", response_model=LatexResponse)
async def compile_latex(
    request: LatexRequest,
    background_tasks: BackgroundTasks,
    compiler: LatexCompiler = Depends()
):
    job_id = str(uuid.uuid4())
    success, result = await compiler.compile_latex(request.content, job_id)
    
    if success:
        pdf_url = f"/pdf/{result}"
        return LatexResponse(
            status="success",
            result=pdf_url,
            job_id=job_id
        )
    else:
        return LatexResponse(
            status="error",
            result={"error": result},
            job_id=job_id
        )

@router.get("/health", response_model=HealthCheck)
async def health_check(compiler: LatexCompiler = Depends()):
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.VERSION,
        active_workers=compiler.executor._max_workers
    )