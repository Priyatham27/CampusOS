from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
from fastapi import Request
import logging

from app.academic.resolver import AcademicResolver
from app.academic.context import set_academic_context, reset_academic_context

logger = logging.getLogger("campusos.middleware.academic")

class AcademicMiddleware(BaseHTTPMiddleware):
    """
    FastAPI HTTP Middleware that runs after IdentityMiddleware. Resolves headers
    (like X-Academic-Year-ID, X-Semester-ID, etc.) into a Request-bound AcademicContext.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Skip resolving for open paths
        if request.url.path in ["/", "/openapi.json", "/docs", "/redoc", "/favicon.ico"]:
            return await call_next(request)

        # 2. Check if identity context is present
        identity_context = getattr(request.state, "identity_context", None)
        if not identity_context or not identity_context.organization:
            # Bypass context resolution if unauthenticated or no organization belongs to request
            return await call_next(request)

        try:
            org_id = identity_context.organization.id
            resolver = AcademicResolver()
            
            # Resolve headers
            context = await resolver.resolve_academic_context(org_id, dict(request.headers))
            
            # Bind context to request state and contextvar
            request.state.academic_context = context
            token = set_academic_context(context)
            try:
                return await call_next(request)
            finally:
                reset_academic_context(token)

        except Exception as e:
            logger.exception("Unexpected error in AcademicMiddleware processing")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal error occurred resolving academic context coordinates.",
                    "data": None,
                    "meta": {},
                    "errors": [str(e)]
                }
            )
