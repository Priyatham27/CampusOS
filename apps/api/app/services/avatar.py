import os
import uuid
import logging
from fastapi import UploadFile
from apps.api.app.core.user_exceptions import AvatarUploadFailed

logger = logging.getLogger("campusos.services.avatar")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

class AvatarService:
    """
    AvatarService validates profile avatar image parameters (type, file size)
    and handles saving files locally or to static directories.
    """

    async def upload_avatar(self, file: UploadFile) -> str:
        """
        Validates the file and saves it locally.
        Returns the relative static URL for retrieving the file.
        """
        # 1. Content-Type check
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise AvatarUploadFailed(
                f"Unsupported image type '{file.content_type}'. Supported: JPEG, PNG, GIF, WEBP."
            )

        # 2. File size check (read chunk size)
        size = 0
        contents = await file.read(1024 * 1024)  # Read 1MB chunk
        while contents:
            size += len(contents)
            if size > MAX_FILE_SIZE:
                raise AvatarUploadFailed(f"File size exceeds the 5MB upload limit.")
            contents = await file.read(1024 * 1024)

        # Reset read pointer
        await file.seek(0)

        # 3. Create static directories and save file
        try:
            # We save in the workspace public directory
            upload_dir = os.path.join("apps", "api", "static", "uploads", "avatars")
            os.makedirs(upload_dir, exist_ok=True)

            # Create secure unique name
            ext = os.path.splitext(file.filename or "")[1] or ".png"
            filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(upload_dir, filename)

            # Write file to disk
            with open(file_path, "wb") as f:
                f.write(await file.read())

            logger.info(f"Avatar file saved locally to {file_path}")

            # Return the access URL path
            return f"/static/uploads/avatars/{filename}"

        except Exception as e:
            logger.exception("Failed to write avatar file locally.")
            raise AvatarUploadFailed(f"Writing profile avatar file failed: {str(e)}")
