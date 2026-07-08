from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import re

HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}){1,2}$")

def validate_hex_color(value: str) -> str:
    if not HEX_COLOR_REGEX.match(value):
        raise ValueError(f"Invalid Hex Color pattern: {value}. Must be a valid hex color (e.g., #4F46E5)")
    return value

class BaseCamelSchema(BaseModel):
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

class BrandingUpdateSchema(BaseCamelSchema):
    primary_color: Optional[str] = Field(None, alias="primaryColor")
    secondary_color: Optional[str] = Field(None, alias="secondaryColor")
    accent_color: Optional[str] = Field(None, alias="accentColor")
    surface_color: Optional[str] = Field(None, alias="surfaceColor")
    background_color: Optional[str] = Field(None, alias="backgroundColor")
    text_primary_color: Optional[str] = Field(None, alias="textPrimaryColor")
    text_secondary_color: Optional[str] = Field(None, alias="textSecondaryColor")
    text_muted_color: Optional[str] = Field(None, alias="textMutedColor")
    text_on_primary: Optional[str] = Field(None, alias="textOnPrimary")
    text_on_secondary: Optional[str] = Field(None, alias="textOnSecondary")
    success_color: Optional[str] = Field(None, alias="successColor")
    warning_color: Optional[str] = Field(None, alias="warningColor")
    danger_color: Optional[str] = Field(None, alias="dangerColor")
    info_color: Optional[str] = Field(None, alias="infoColor")
    border_radius: Optional[str] = Field(None, alias="borderRadius")
    font_family: Optional[str] = Field(None, alias="fontFamily")
    theme: Optional[str] = Field(None)
    default_landing_image: Optional[str] = Field(None, alias="defaultLandingImage")
    certificate_watermark: Optional[str] = Field(None, alias="certificateWatermark")
    email_header_logo: Optional[str] = Field(None, alias="emailHeaderLogo")
    email_footer: Optional[str] = Field(None, alias="emailFooter")
    footer_text: Optional[str] = Field(None, alias="footerText")
    support_email: Optional[EmailStr] = Field(None, alias="supportEmail")
    website: Optional[str] = Field(None)
    social_twitter: Optional[str] = Field(None, alias="socialTwitter")
    social_linkedin: Optional[str] = Field(None, alias="socialLinkedin")
    social_facebook: Optional[str] = Field(None, alias="socialFacebook")
    social_instagram: Optional[str] = Field(None, alias="socialInstagram")
    social_youtube: Optional[str] = Field(None, alias="socialYoutube")

    @field_validator(
        "primary_color", "secondary_color", "accent_color", "surface_color",
        "background_color", "text_primary_color", "text_secondary_color",
        "text_muted_color", "text_on_primary", "text_on_secondary",
        "success_color", "warning_color", "danger_color", "info_color"
    )
    @classmethod
    def validate_colors(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_hex_color(v)
        return v

    @field_validator(
        "default_landing_image", "certificate_watermark", "email_header_logo",
        "website", "social_twitter", "social_linkedin", "social_facebook",
        "social_instagram", "social_youtube"
    )
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("light", "dark", "auto"):
            raise ValueError("Theme must be light, dark, or auto")
        return v

class BrandingResponseSchema(BaseCamelSchema):
    organization_id: str = Field(..., alias="organizationId")
    organization_logo: Optional[str] = Field(None, alias="organizationLogo")
    dark_logo: Optional[str] = Field(None, alias="darkLogo")
    favicon: Optional[str] = Field(None, alias="favicon")
    banner: Optional[str] = Field(None, alias="banner")
    primary_color: str = Field(..., alias="primaryColor")
    secondary_color: str = Field(..., alias="secondaryColor")
    accent_color: str = Field(..., alias="accentColor")
    surface_color: str = Field(..., alias="surfaceColor")
    background_color: str = Field(..., alias="backgroundColor")
    text_primary_color: str = Field(..., alias="textPrimaryColor")
    text_secondary_color: str = Field(..., alias="textSecondaryColor")
    text_muted_color: str = Field(..., alias="textMutedColor")
    text_on_primary: str = Field(..., alias="textOnPrimary")
    text_on_secondary: str = Field(..., alias="textOnSecondary")
    success_color: str = Field(..., alias="successColor")
    warning_color: str = Field(..., alias="warningColor")
    danger_color: str = Field(..., alias="dangerColor")
    info_color: str = Field(..., alias="infoColor")
    border_radius: str = Field(..., alias="borderRadius")
    font_family: str = Field(..., alias="fontFamily")
    theme: str
    default_landing_image: Optional[str] = Field(None, alias="defaultLandingImage")
    certificate_watermark: Optional[str] = Field(None, alias="certificateWatermark")
    email_header_logo: Optional[str] = Field(None, alias="emailHeaderLogo")
    email_footer: Optional[str] = Field(None, alias="emailFooter")
    footer_text: Optional[str] = Field(None, alias="footerText")
    support_email: Optional[EmailStr] = Field(None, alias="supportEmail")
    website: Optional[str] = None
    social_twitter: Optional[str] = Field(None, alias="socialTwitter")
    social_linkedin: Optional[str] = Field(None, alias="socialLinkedin")
    social_facebook: Optional[str] = Field(None, alias="socialFacebook")
    social_instagram: Optional[str] = Field(None, alias="socialInstagram")
    social_youtube: Optional[str] = Field(None, alias="socialYoutube")
    version: int
    css_variables: Optional[str] = Field(None, alias="cssVariables")
    tailwind_tokens: Optional[Dict[str, Any]] = Field(None, alias="tailwindTokens")

    @field_validator("organization_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        return str(v)

class BrandingRevisionResponseSchema(BaseCamelSchema):
    id: str = Field(..., alias="id")
    branding_id: str = Field(..., alias="brandingId")
    organization_id: str = Field(..., alias="organizationId")
    version: int
    branding_data: Dict[str, Any] = Field(..., alias="brandingData")

    @field_validator("id", "branding_id", "organization_id", mode="before")
    @classmethod
    def serialize_object_id(cls, v: Any) -> str:
        return str(v)
