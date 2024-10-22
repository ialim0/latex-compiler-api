from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time
import logging
from app.api.routes import router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                "Request processed",
                extra={
                    "props": {
                        "method": request.method,
                        "path": request.url.path,
                        "process_time": f"{process_time:.3f}s",
                        "status_code": response.status_code
                    }
                }
            )

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "props": {
                        "method": request.method,
                        "path": request.url.path,
                        "process_time": f"{process_time:.3f}s",
                        "error": str(e)
                    }
                }
            )
            raise

# app/main.py (update the middleware section)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.middleware import RequestLoggingMiddleware
from app.config import settings  # Adjust as per your project structure

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Add middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specify your allowed methods
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # Setup routes
    app.include_router(router, prefix=settings.API_V1_STR)

    return app
