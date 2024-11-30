# app/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore

from app.api.routes import router
from app.api.middleware import RequestLoggingMiddleware
from app.core.logging import setup_logging
from app.config import get_settings
from app.services.cache import RedisCache


class FastAPIApp:
    def __init__(self):
        self.settings = get_settings()
        self.app = FastAPI(
            title=self.settings.PROJECT_NAME,
            version=self.settings.VERSION,
            docs_url="/api/docs",
            redoc_url="/api/redoc",
        )
        self.setup_middlewares()
        self.setup_routes()
        self.setup_instrumentation()
        self.setup_events()

    def setup_middlewares(self):
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        self.app.add_middleware(RequestLoggingMiddleware)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.CORS_ORIGINS,
            allow_methods=self.settings.CORS_ALLOW_METHODS,
            allow_headers=self.settings.CORS_ALLOW_HEADERS,
        )

    def setup_routes(self):
        self.app.include_router(router, prefix=self.settings.API_V1_STR)
        self.app.mount("/pdf", StaticFiles(directory=self.settings.OUTPUT_DIR), name="pdf")

    def setup_instrumentation(self):
        Instrumentator().instrument(self.app).expose(self.app)

    def setup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            setup_logging()
            redis_cache = RedisCache()
            await redis_cache.init_pool()

    def run(self):
        uvicorn.run(
            "main:app",
            host=self.settings.HOST,
            port=self.settings.PORT,
            workers=self.settings.WORKERS,
            loop="uvloop"
        )


fastapi_app_instance = FastAPIApp()
app = fastapi_app_instance.app

if __name__ == "__main__":
    fastapi_app_instance.run()
