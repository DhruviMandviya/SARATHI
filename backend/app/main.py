from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.routers import (
    auth,
    applications,
    documents,
    findings,
    verification,
    compliance,
    admin,
    reports,
    decisions,
    dashboard,
    audit,
    notifications,
    information_requests,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    from backend.app.core.database import SessionLocal, run_auto_migrations
    run_auto_migrations(engine)
    try:
        from backend.app.services.notice_sync import sync_unpersisted_info_requested_notices
        db = SessionLocal()
        sync_unpersisted_info_requested_notices(db)
        db.close()
    except Exception as e:
        print(f"[STARTUP_SYNC_WARN] Notice synchronization: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

cors_origins = list(dict.fromkeys(ALLOWED_ORIGINS + (settings.CORS_ORIGINS or [])))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(applications.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(findings.router, prefix=settings.API_V1_STR)
app.include_router(verification.router, prefix=settings.API_V1_STR)
app.include_router(compliance.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(decisions.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(information_requests.router, prefix=settings.API_V1_STR)

@app.get("/")
@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_docs": f"{settings.API_V1_STR}/docs"
    }
