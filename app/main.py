# main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import router
from app.api.middleware import RequestLoggingMiddleware
from app.core.logging import setup_logging
from app.config import settings
from app.services.cache import RedisCache

redis_cache = RedisCache()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(router, prefix=settings.API_V1_STR)
    
    app.mount("/pdf", StaticFiles(directory=settings.OUTPUT_DIR), name="pdf")
    
    if settings.ENABLE_METRICS:
        Instrumentator().instrument(app).expose(app)
    
    return app

app = create_application()

@app.on_event("startup")
async def startup_event():
    
    setup_logging()
    
    await redis_cache.init_client()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        loop="uvloop",
    )
