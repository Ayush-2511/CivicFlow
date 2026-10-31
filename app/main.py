"""CivicFlow FastAPI Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app import __version__

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

