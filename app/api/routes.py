from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import LatexRequest, LatexResponse, HealthCheck
from app.services.latex_compiler import LatexCompiler
from app.config import get_settings
import uuid
from datetime import datetime
from app.core.exceptions import LatexCompilationError

router = APIRouter()
settings = get_settings()

@router.post("/compile", response_model=LatexResponse)
async def compile_latex(
    request: LatexRequest,
    compiler: LatexCompiler = Depends()
):
    try:
        job_id = str(uuid.uuid4())
        success, result = await compiler.compile_latex(request.content, job_id)
        
        if success:
            # Result is now the full S3 URL, no need to modify it
            return LatexResponse(
                status="success",
                result=result,  # Direct S3 URL from the compiler
                job_id=job_id
            )
        else:
            raise LatexCompilationError(result)
            
    except LatexCompilationError as e:
        return LatexResponse(
            status="error",
            result={"error": str(e)},
            job_id=job_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/health", response_model=HealthCheck)
async def health_check(compiler: LatexCompiler = Depends()):
    try:
        s3_status = "healthy" if compiler.s3_storage.s3_client.list_buckets() else "unhealthy"
        
        return HealthCheck(
            status="healthy" if s3_status == "healthy" else "degraded",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            active_workers=compiler.executor._max_workers,
            storage_status=s3_status
        )
    except Exception as e:
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            active_workers=compiler.executor._max_workers,
            storage_status="unhealthy",
            error=str(e)
        )