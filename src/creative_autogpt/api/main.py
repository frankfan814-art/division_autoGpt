"""
FastAPI application factory
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from creative_autogpt.api.schemas.response import HealthResponse
from creative_autogpt.utils.config import get_settings
from creative_autogpt.api.routes import sessions, websocket, prompts
from creative_autogpt.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Creative AutoGPT API")
    setup_logger()

    settings = get_settings()

    # Initialize any resources here
    # (e.g., database connections, LLM clients)

    yield

    # Shutdown
    logger.info("Shutting down Creative AutoGPT API")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application

    Returns:
        Configured FastAPI app
    """
    settings = get_settings()

    app = FastAPI(
        title="Creative AutoGPT API",
        description="AI-powered creative writing system for long-form novels",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(sessions.router)
    app.include_router(websocket.router)
    app.include_router(prompts.router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Creative AutoGPT API",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs" if settings.is_development else None,
        }

    # Health check
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint"""
        from creative_autogpt.utils.llm_client import MultiLLMClient

        llm_client = MultiLLMClient()
        providers = llm_client.get_available_providers()

        return HealthResponse(
            status="healthy",
            version="0.1.0",
            llm_providers=providers,
            storage_status="ok",
            memory_status="ok",
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.is_development else "An error occurred",
            },
        )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"{request.method} {request.url.path} - {response.status_code}")
        return response

    return app


# Create app instance for uvicorn/dashscope
app = create_app()
