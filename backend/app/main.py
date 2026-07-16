from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from beanie import init_beanie
from app.core.config import settings
from app.core.database import db_manager
from app.core.logger import logger
from app.middleware.tenant_middleware import TenantMiddleware
from app.middleware.identity_middleware import IdentityMiddleware
from app.middleware.request_context_middleware import RequestContextMiddleware
from app.middleware.request_logging_middleware import RequestLoggingMiddleware
from app.api.v1.router import api_router
from app.models.org_engine import ORG_ENGINE_MODELS
from app.models.identity import IDENTITY_MODELS

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
            # Run startup bootstrapping for identity components
            from app.services.identity_bootstrap import IdentityBootstrapService
            bootstrap_svc = IdentityBootstrapService()
            await bootstrap_svc.bootstrap()
            logger.info("Lifespan startup sequence completed successfully.")
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

# Register Tenant and Identity Middleware pipeline
app.add_middleware(TenantMiddleware)
app.add_middleware(IdentityMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestContextMiddleware)

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

from app.core.exceptions import OrganizationException
from app.core.credential_exceptions import CredentialException
from app.core.auth_exceptions import AuthenticationException
from app.core.session_exceptions import SessionException
from app.core.authorization_exceptions import AuthorizationException
from app.core.user_exceptions import UserException
from app.academic.exceptions import AcademicException

@app.exception_handler(UserException)
async def user_exception_handler(request: Request, exc: UserException):
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

@app.exception_handler(AcademicException)
async def academic_exception_handler(request: Request, exc: AcademicException):
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

@app.exception_handler(AuthorizationException)
async def authorization_exception_handler(request: Request, exc: AuthorizationException):
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

@app.exception_handler(SessionException)
async def session_exception_handler(request: Request, exc: SessionException):
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

@app.exception_handler(CredentialException)
async def credential_exception_handler(request: Request, exc: CredentialException):
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

@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(request: Request, exc: AuthenticationException):
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
