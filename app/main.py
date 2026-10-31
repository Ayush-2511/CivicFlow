"""CivicFlow FastAPI Application Entrypoint."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.exceptions import CivicFlowError, NotAPolicy, ProviderError, UnreadableDocument
from app.providers.sources import sources_fetcher
from app.routes.pipeline import router as pipeline_router
from app.routes.session import router as session_router

app = FastAPI(
    title="CivicFlow API",
    description="Multilingual Policy, Rights & Scheme Explainer",
    version=__version__,
    debug=settings.DEBUG,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers mapping typed errors to clear JSON responses
@app.exception_handler(UnreadableDocument)
async def unreadable_document_handler(request: Request, exc: UnreadableDocument):
    return JSONResponse(
        status_code=422,
        content={
            "error": "UnreadableDocument",
            "message": exc.message,
            "suggestion": "Please provide a clearer PDF or take a well-lit photo of the official document.",
            "details": exc.details,
        },
    )


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    return JSONResponse(
        status_code=502,
        content={
            "error": "ProviderError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(NotAPolicy)
async def not_a_policy_handler(request: Request, exc: NotAPolicy):
    return JSONResponse(
        status_code=400,
        content={
            "error": "NotAPolicy",
            "message": exc.message,
            "details": exc.details,
        },
    )


# Serve synthesized audio files
settings.ensure_directories()
app.mount("/audio", StaticFiles(directory=str(settings.AUDIO_OUTPUT_DIR)), name="audio")

# Mount API Routers
app.include_router(pipeline_router)
app.include_router(session_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Service health and capability probe."""
    return {
        "status": "healthy",
        "service": "CivicFlow",
        "version": __version__,
        "environment": settings.APP_ENV,
        "supported_languages": settings.SUPPORTED_LANGUAGES,
    }


@app.get("/sources/verified", tags=["Sources"])
async def list_verified_sources() -> list:
    """List verified official government scheme sources for live demo."""
    return sources_fetcher.get_verified_demo_sources()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

