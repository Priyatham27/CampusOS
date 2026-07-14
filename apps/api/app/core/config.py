import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "CampusOS API"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    @model_validator(mode="before")
    @classmethod
    def map_alternate_env_vars(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Map ENVIRONMENT -> ENV
            if "ENVIRONMENT" in values and "ENV" not in values:
                values["ENV"] = values["ENVIRONMENT"]
            # Map MONGODB_URI -> MONGODB_URL
            if "MONGODB_URI" in values and "MONGODB_URL" not in values:
                values["MONGODB_URL"] = values["MONGODB_URI"]
            # Map JWT_SECRET -> SECRET_KEY
            if "JWT_SECRET" in values and "SECRET_KEY" not in values:
                values["SECRET_KEY"] = values["JWT_SECRET"]
        return values
    
    # Security & Tokens
    SECRET_KEY: str = Field(default="supersecretkeyforcampusosmvpdevelopmentphase1", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    
    # Cookies
    ACCESS_COOKIE_KEY: str = "campusos_access_token"
    REFRESH_COOKIE_KEY: str = "campusos_refresh_token"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "https://campusos.vercel.app"]
    
    # Databases
    MONGODB_URL: str = Field(default="mongodb://localhost:27017/campusos", env="MONGODB_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Cloudinary Placeholder Config
    CLOUDINARY_CLOUD_NAME: str = Field(default="campusos-dev", env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = Field(default="api_key_placeholder", env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = Field(default="api_secret_placeholder", env="CLOUDINARY_API_SECRET")
    
    # Default Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = {
        "enable_events": False,
        "enable_attendance": False,
        "enable_certificates": False,
        "enable_clubs": False,
        "enable_analytics": False,
        "enable_audit_logs": True,
        "enable_file_uploads": True,
    }
    
    # Default Tenant
    DEFAULT_TENANT_SLUG: str = "campusos-main"

    class Config:
        case_sensitive = True
        extra = "ignore"
        # Resolve the .env file path dynamically relative to this configuration file
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env"
        )

settings = Settings()
