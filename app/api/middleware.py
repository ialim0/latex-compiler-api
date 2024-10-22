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


