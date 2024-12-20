from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from app.models.schemas import LatexRequest, LatexResponse, HealthCheck
from app.services.latex_compiler import LatexCompiler
from app.config import get_settings
import uuid
from datetime import datetime
from app.core.exceptions import LatexCompilationError

router = APIRouter()
settings = get_settings()

async def validate_user_id(x_user_id: str = Header(..., description="User ID from authentication system")):
    """Validate the user ID from the request header"""
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID is required"
        )
    return x_user_id

@router.post("/compile", response_model=LatexResponse)
async def compile_latex(
    request: LatexRequest,
    user_id: str = Depends(validate_user_id),
    compiler: LatexCompiler = Depends()
):
    """
    Compile LaTeX content to PDF and store in S3 with user-specific access
    
    Args:
        request: LaTeX content to compile
        user_id: Authenticated user's ID from request header
        compiler: LaTeX compiler instance
    
    Returns:
        LatexResponse with compilation status and secure access URL
    """
    try:
        job_id = str(uuid.uuid4())
        success, result = await compiler.compile_latex(
            content=request.content,
            job_id=job_id,
            user_id=user_id
        )
        
        if success:
            return LatexResponse(
                status="success",
                result={
                    "url": result["url"],  # Presigned URL for immediate access
                    "key": result["key"],  # S3 key for future reference
                    "expires_in": 3600  # URL expiration time in seconds
                },
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
        logger.error(f"Unexpected error in compile_latex: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/documents/{s3_key}/url")
async def refresh_document_url(
    s3_key: str,
    user_id: str = Depends(validate_user_id),
    compiler: LatexCompiler = Depends()
):
    """
    Generate a new presigned URL for an existing document
    
    Args:
        s3_key: The S3 key of the document
        user_id: Authenticated user's ID from request header
        compiler: LaTeX compiler instance
    
    Returns:
        Dict containing new presigned URL and expiration time
    """
    try:
        # Verify the requested key belongs to the user
        expected_prefix = f"cvs/{user_id}/"
        if not s3_key.startswith(expected_prefix):
            raise HTTPException(
                status_code=403,
                detail="Access denied to this document"
            )
            
        new_url = await compiler.s3_storage.get_presigned_url(s3_key)
        return {
            "url": new_url,
            "expires_in": 3600
        }
        
    except Exception as e:
        logger.error(f"Error refreshing document URL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh document URL: {str(e)}"
        )

@router.get("/health", response_model=HealthCheck)
async def health_check(compiler: LatexCompiler = Depends()):
    """Check the health status of the compiler service and its dependencies"""
    try:
        # Test S3 connectivity
        s3_status = "healthy"
        try:
            await asyncio.to_thread(compiler.s3_storage.s3_client.list_buckets)
        except Exception as e:
            s3_status = "unhealthy"
            logger.error(f"S3 health check failed: {str(e)}")
        
        return HealthCheck(
            status="healthy" if s3_status == "healthy" else "degraded",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            active_workers=compiler.executor._max_workers,
            storage_status=s3_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            active_workers=compiler.executor._max_workers,
            storage_status="unhealthy",
            error=str(e)
        )