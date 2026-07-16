from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
import motor.motor_asyncio
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings
from app.core.logger import logger
from app.middleware.auth import requires_permission
from app.models.models import generate_prefixed_id, User
from app.schemas.schemas import APIResponse

router = APIRouter()

@router.post("", response_model=APIResponse[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(requires_permission("upload:file"))
):
    """Uploads a file using Cloudinary integration placeholder, returning simulated URL payload."""
    logger.info(f"Uploading file '{file.filename}' by user {current_user.email} in tenant {current_user.tenant_id}...")
    
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Supported: JPEG, PNG, GIF, WEBP, PDF."
        )

    mock_url = f"https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=800"
    if "logo" in file.filename.lower():
        mock_url = "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=128&h=128&fit=crop"

    return {
        "success": True,
        "message": "File uploaded successfully.",
        "data": {
            "filename": file.filename,
            "content_type": file.content_type,
            "url": mock_url,
            "uploaded_at": datetime.utcnow().isoformat()
        },
        "meta": {},
        "errors": []
    }
