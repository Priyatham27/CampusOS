from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from fastapi import Request
from app.core.request_context import set_request, reset_request

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that binds the incoming FastAPI Request object to a thread-local/async-local
    ContextVar. Downstream code (loggers, services) can use this to inspect headers, IP, etc.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        token = set_request(request)
        try:
            return await call_next(request)
        finally:
            reset_request(token)
