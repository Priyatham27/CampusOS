import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Union, Any, Optional
from fastapi import Response, Request
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings
from app.core.logger import logger

# Thread-safe Argon2id password hasher with secure defaults
ph = PasswordHasher()

def hash_password_argon2(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)

def verify_password_argon2(plain_password: str, hashed_password: str) -> bool:
    """Verify Argon2id password match."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception as e:
        logger.error(f"Error verifying password with Argon2id: {e}")
        return False


def hash_password(password: str) -> str:
    """Hash password using direct bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify standard bcrypt password match."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Generate a short-lived access JWT token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Generate a long-lived refresh JWT token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Union[str, None]:
    """Decode and validate a JWT token."""
    try:
        decoded_payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        # Ensure it is an access token
        if decoded_payload.get("type") != "access":
            logger.warning("Decoded token is not of type 'access'")
            return None
        return decoded_payload.get("sub")
    except jwt.PyJWTError as e:
        logger.warning(f"Failed to decode access token: {e}")
        return None

def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Inject access and refresh tokens directly into HttpOnly secure cookies."""
    is_prod = settings.ENV == "production"
    
    # Access token cookie
    response.set_cookie(
        key=settings.ACCESS_COOKIE_KEY,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=is_prod,
        samesite="lax" if not is_prod else "none",
        path="/"
    )
    
    # Refresh token cookie
    response.set_cookie(
        key=settings.REFRESH_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        secure=is_prod,
        samesite="lax" if not is_prod else "none",
        path="/"
    )

def clear_auth_cookies(response: Response) -> None:
    """Delete access and refresh token cookies from response headers."""
    is_prod = settings.ENV == "production"
    response.delete_cookie(key=settings.ACCESS_COOKIE_KEY, path="/", samesite="lax" if not is_prod else "none", secure=is_prod)
    response.delete_cookie(key=settings.REFRESH_COOKIE_KEY, path="/", samesite="lax" if not is_prod else "none", secure=is_prod)

def extract_access_token(request: Request) -> Optional[str]:
    """Extract authorization access token from incoming request HTTP cookies or Auth headers."""
    # 1. Try cookies first
    cookie_token = request.cookies.get(settings.ACCESS_COOKIE_KEY)
    if cookie_token:
        return cookie_token
        
    # 2. Fallback to Authorization Bearer header (for standalone API tests/scripts!)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ")[1]
        
    return None
