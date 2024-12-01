# app/main.py
import os
import multiprocessing
import gunicorn.app.base
from fastapi import FastAPI
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
            openapi_url="/api/openapi.json",
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
  

    def setup_instrumentation(self):
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True
        ).instrument(self.app).expose(self.app, include_in_schema=False)

    def setup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            setup_logging()
            redis_cache = RedisCache()
            await redis_cache.init_pool()
            self.app.state.redis_cache = redis_cache

        @self.app.on_event("shutdown")
        async def shutdown_event():
            redis_cache: RedisCache = self.app.state.redis_cache
            redis_cache.pool.close()
            await redis_cache.pool.wait_closed()

    def run(self):
        workers = self.settings.WORKERS or (multiprocessing.cpu_count() * 2 + 1)
        os.system(
            f"gunicorn app.main:app "
            f"--workers {workers} "
            f"--worker-class uvicorn.workers.UvicornWorker "
            f"--bind {self.settings.HOST}:{self.settings.PORT} "
            f"--loop uvloop "
            f"--timeout 120 "
            f"--keep-alive 5 "
            f"--access-logfile - "
            f"--error-logfile -"
        )


fastapi_app_instance = FastAPIApp()
app = fastapi_app_instance.app

if __name__ == "__main__":
    fastapi_app_instance.run()
