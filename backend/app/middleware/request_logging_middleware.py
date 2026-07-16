import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from fastapi import Request
from app.core.identity_context import get_identity_context

logger = logging.getLogger("campusos.middleware.logging")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware that logs request parameters, tracks latency,
    and captures responses, ensuring sensitive data is sanitized.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Ignore static assets and docs from logs clutter
        if request.url.path in ["/openapi.json", "/docs", "/redoc", "/favicon.ico"]:
            return await call_next(request)

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        query = request.url.query
        client_host = request.client.host if request.client else "unknown"

        # Log request receipt
        logger.info(f"Incoming: {method} {path} from {client_host} (Query: {query})")

        response = None
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Latency on crash
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(f"Request failed: {method} {path} - Error: {e} - Duration: {duration:.2f}ms")
            raise e
        finally:
            if response:
                duration = (time.perf_counter() - start_time) * 1000
                status_code = response.status_code
                
                # Fetch user details if logged in
                ctx = get_identity_context()
                user_email = ctx.user.email if ctx and ctx.user else "Anonymous"
                org_slug = ctx.organization.slug if ctx and ctx.organization else "NoTenant"

                log_msg = f"Completed: {method} {path} - Status: {status_code} - Org: {org_slug} - User: {user_email} - Duration: {duration:.2f}ms"
                if status_code >= 500:
                    logger.error(log_msg)
                elif status_code >= 400:
                    logger.warning(log_msg)
                else:
                    logger.info(log_msg)
