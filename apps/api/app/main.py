from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from beanie import init_beanie
from apps.api.app.core.config import settings
from apps.api.app.core.database import db_manager
from apps.api.app.core.logger import logger
from apps.api.app.middleware.tenant_middleware import TenantMiddleware
from apps.api.app.api.v1.router import api_router
from apps.api.app.models.org_engine import ORG_ENGINE_MODELS
from apps.api.app.models.identity import IDENTITY_MODELS

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database connections on startup...")
    try:
        db_manager.connect()
        if db_manager.db is not None:
            logger.info("Initializing Beanie ODM with document models...")
            await init_beanie(
                database=db_manager.db,
                document_models=ORG_ENGINE_MODELS + IDENTITY_MODELS
            )
            logger.info("Beanie ODM initialization completed successfully.")
    except Exception as e:
        logger.error(f"Database setup error during startup lifecycle: {e}")
    yield
    # Shutdown actions
    logger.info("Closing database connections on shutdown...")
    db_manager.disconnect()

app = FastAPI(
    title=settings.APP_NAME,
    description="CampusOS Platform Foundation APIs supporting white-labeled Multi-Tenant SaaS systems.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware config - CRITICAL: must match frontend ports and support credentials!
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Tenant Context Middleware
app.add_middleware(TenantMiddleware)

# Standardized Error Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
    logger.warning(f"Request validation failed on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed: request payload parameters are invalid.",
            "data": None,
            "meta": {},
            "errors": errors
        }
    )

from apps.api.app.core.exceptions import OrganizationException

@app.exception_handler(OrganizationException)
async def organization_exception_handler(request: Request, exc: OrganizationException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "meta": {},
            "errors": [exc.__class__.__name__]
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "meta": {},
            "errors": [f"HTTP_{exc.status_code}"]
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception occurred during request to {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred. Please contact support.",
            "data": None,
            "meta": {},
            "errors": [str(exc)]
        }
    )

# Root status check endpoint
@app.get("/", tags=["Status"])
async def status_check():
    return {
        "success": True,
        "message": "CampusOS Platform Engine is active.",
        "data": {
            "status": "online",
            "service": settings.APP_NAME,
            "environment": settings.ENV,
            "database": "connected" if db_manager.client is not None else "disconnected",
            "cache": "online" if db_manager.redis_client is not None else "offline"
        },
        "meta": {},
        "errors": []
    }

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
