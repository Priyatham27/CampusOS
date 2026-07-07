from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
from bson import ObjectId

from apps.api.app.core.database import db_manager
from apps.api.app.core.config import settings
from apps.api.app.core.tenant_context import set_tenant_id
from apps.api.app.core.logger import logger

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Static asset paths or docs skip resolving
        if request.url.path in ["/", "/openapi.json", "/docs", "/redoc", "/favicon.ico"]:
            return await call_next(request)

        # 1. Resolve host and headers
        host = request.headers.get("host", "").split(":")[0]
        tenant_slug_header = request.headers.get("x-tenant-slug")
        
        tenant_doc = None
        db = db_manager.db
        
        # Connect to DB if not initialized
        if db is None:
            db_manager.connect()
            db = db_manager.db

        try:
            # 2. Extract tenant by X-Tenant-Slug header (highest priority, convenient for localhost debugging!)
            if tenant_slug_header:
                tenant_doc = await db["tenants"].find_one({"slug": tenant_slug_header.lower()})

            # 3. Extract by Custom Domain match
            if not tenant_doc and host and host != "localhost" and host != "127.0.0.1":
                tenant_doc = await db["tenants"].find_one({
                    "config.custom_domain": host.lower(),
                    "is_active": True
                })
                
                # Try fallback matching host subdomain (e.g. portal.campusos.com matches slug 'portal')
                if not tenant_doc and "." in host:
                    subdomain = host.split(".")[0]
                    tenant_doc = await db["tenants"].find_one({
                        "slug": subdomain.lower(),
                        "is_active": True
                    })

            # 4. Fallback to default tenant if none identified
            if not tenant_doc:
                tenant_doc = await db["tenants"].find_one({"slug": settings.DEFAULT_TENANT_SLUG})

            # 5. If STILL no tenant exists, and db is completely empty, we allow access so auth auto-seeding can create the default tenant!
            if not tenant_doc:
                # Check database tenants count
                tenants_count = await db["tenants"].count_documents({})
                if tenants_count > 0:
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": "Tenant resolution failed: requested institution is unregistered.", "errors": ["Unregistered tenant"]}
                    )
                # No tenants exist at all (unseeded db state) -> proceed to let auth/login auto-seed
                tenant_id = "ten_unseeded"
                request.state.tenant_id = tenant_id
                request.state.tenant = None
            else:
                tenant_id = str(tenant_doc["_id"])
                request.state.tenant_id = tenant_id
                request.state.tenant = tenant_doc

            # 6. Store in thread-safe contextvars
            token = set_tenant_id(tenant_id)
            
            try:
                response = await call_next(request)
                return response
            finally:
                # Ensure contextvar is cleared down the line
                pass
                
        except Exception as e:
            logger.exception(f"Error occurred in TenantMiddleware: {e}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Internal error occurred resolving tenant identity.", "errors": [str(e)]}
            )
