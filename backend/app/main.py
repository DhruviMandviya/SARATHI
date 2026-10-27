from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized error response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Don't mask HTTPExceptions
    if hasattr(exc, "status_code"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": getattr(exc, "code", "HTTP_ERROR")}
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"}
    )

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_docs": f"{settings.API_V1_STR}/docs"
    }
