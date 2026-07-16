from abc import ABC, abstractmethod
import time
import hashlib
from typing import Optional
from fastapi import UploadFile
import httpx

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import UploadFailed

class StorageProvider(ABC):
    """
    Abstract interface for multi-tenant file storage.
    Enables future S3 migration without altering business layers.
    """
    @abstractmethod
    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str) -> str:
        """Uploads file bytes and returns the public URL."""
        pass

    @abstractmethod
    async def delete(self, public_url: str) -> bool:
        """Deletes a file by its public URL."""
        pass

class CloudinaryStorageProvider(StorageProvider):
    """
    Production-grade Cloudinary Storage Provider.
    Performs signature-based direct REST upload using httpx.
    Falls back to secure simulated CDN URLs if placeholders or invalid credentials are set.
    """

    def __init__(self):
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
        self.api_key = settings.CLOUDINARY_API_KEY
        self.api_secret = settings.CLOUDINARY_API_SECRET
        self.is_placeholder = (
            "placeholder" in self.api_key.lower() 
            or "placeholder" in self.api_secret.lower()
            or "dev" in self.api_key.lower()
        )

    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str) -> str:
        if self.is_placeholder:
            logger.info("Using simulated Cloudinary upload fallback (placeholder credentials detected).")
            # Generate a structured mockup URL
            timestamp = int(time.time())
            safe_name = "".join(c for c in filename if c.isalnum() or c in "._-").lower()
            return f"https://res.cloudinary.com/{self.cloud_name}/image/upload/v{timestamp}/{folder}/{safe_name}"

        try:
            timestamp = int(time.time())
            # Prepare signature parameters (sorted alphabetically by key)
            params = {
                "folder": folder,
                "timestamp": str(timestamp)
            }
            # Construct signature string: key1=val1&key2=val2<api_secret>
            signature_str = f"folder={folder}&timestamp={timestamp}{self.api_secret}"
            signature = hashlib.sha1(signature_str.encode("utf-8")).hexdigest()

            url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/upload"
            
            data = {
                "api_key": self.api_key,
                "timestamp": str(timestamp),
                "folder": folder,
                "signature": signature
            }
            
            files = {
                "file": (filename, file_content, content_type)
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, files=files, timeout=30.0)
                if response.status_code != 200:
                    logger.error(f"Cloudinary upload REST API failed: status={response.status_code}, error={response.text}")
                    raise UploadFailed(f"Cloudinary upload failed: {response.text}")
                
                result = response.json()
                return result.get("secure_url") or result.get("url")

        except Exception as e:
            if isinstance(e, UploadFailed):
                raise e
            logger.exception(f"Unexpected exception during Cloudinary upload: {e}")
            raise UploadFailed(f"Cloudinary connection failed: {str(e)}")

    async def delete(self, public_url: str) -> bool:
        if self.is_placeholder:
            logger.info(f"Simulating Cloudinary delete for URL: {public_url}")
            return True

        try:
            # Extract public_id from cloudinary URL
            # Example URL: https://res.cloudinary.com/cloud_name/image/upload/v12345/folder/filename.jpg
            # public_id should be "folder/filename" (without extension)
            if "image/upload/" not in public_url:
                return False
            
            path_parts = public_url.split("image/upload/")[-1].split("/")
            # Remove version part (starts with 'v' followed by digits)
            if path_parts[0].startswith("v") and path_parts[0][1:].isdigit():
                path_parts = path_parts[1:]
            
            public_id_with_ext = "/".join(path_parts)
            public_id = public_id_with_ext.rsplit(".", 1)[0]

            timestamp = int(time.time())
            signature_str = f"public_id={public_id}&timestamp={timestamp}{self.api_secret}"
            signature = hashlib.sha1(signature_str.encode("utf-8")).hexdigest()

            url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/destroy"
            
            data = {
                "api_key": self.api_key,
                "timestamp": str(timestamp),
                "public_id": public_id,
                "signature": signature
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, timeout=30.0)
                if response.status_code != 200:
                    logger.error(f"Cloudinary delete failed: status={response.status_code}, error={response.text}")
                    return False
                
                result = response.json()
                return result.get("result") == "ok"

        except Exception as e:
            logger.error(f"Failed to delete resource from Cloudinary: {e}")
            return False

# Injection interface
def get_storage_provider() -> StorageProvider:
    return CloudinaryStorageProvider()
