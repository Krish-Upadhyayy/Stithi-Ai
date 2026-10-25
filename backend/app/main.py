"""FastAPI application entrypoint for SIH Training Centre AI Monitoring System."""

import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.api.router import api_router
from backend.app.schemas.health import HealthStatus

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Unified Python FastAPI backend providing database persistence, compliance rules, and AI pipeline orchestration.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================
# GLOBAL EXCEPTION HANDLERS (No secret/password/stack trace leak)
# ==============================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", [])])
        errors.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "status_code": 422,
            "detail": "; ".join(errors) if errors else "Invalid request payload.",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "status_code": 500,
            "detail": "An internal server error occurred. Please contact the administrator.",
        },
    )


# Root health checks
@app.get("/health", response_model=HealthStatus, summary="Root Health Check", tags=["Health"])
def root_health():
    """Returns direct health confirmation."""
    return HealthStatus(
        status="UP",
        service=settings.APP_NAME,
        environment=settings.APP_ENV,
        architecture="FastAPI + SQLAlchemy + MySQL",
        version="0.2.0",
        pipelines={
            "attendance": "ONLINE (Stithi AI anonymous presence evaluation)",
            "infrastructure": "ONLINE (Stithi AI custom asset evaluation)",
            "compliance_engine": "READY (Comparator operational)",
            "privacy_engine": "READY (Anonymization utility active)",
        }
    )


@app.get("/", summary="Root Index", tags=["Health"])
def root():
    return {
        "service": settings.APP_NAME,
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/health",
        "api_v1": f"{settings.API_PREFIX}",
        "api_v1_health": f"{settings.API_PREFIX}/health",
    }


# Mount central API router with prefix /api/v1
app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
