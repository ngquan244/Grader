"""
Security utilities for authentication and encryption.
Implements industry best practices for password hashing and token encryption.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import base64
import logging

from cryptography.fernet import Fernet
from passlib.context import CryptContext
from jose import jwt, JWTError

from backend.core.config import settings

# Configure logger - NEVER log sensitive data
logger = logging.getLogger(__name__)


# =============================================================================
# Password Hashing
# =============================================================================

# Password context supporting both argon2 and bcrypt
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default=settings.PASSWORD_HASH_ALGORITHM,
    deprecated="auto",
    # Argon2 parameters (secure defaults)
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,
    argon2__parallelism=4,
    # Bcrypt parameters
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(password: str) -> str:
    """
    Hash a password using argon2 or bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification error: {type(e).__name__}")
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if password hash needs to be upgraded to a stronger algorithm.
    
    Args:
        hashed_password: Current password hash
        
    Returns:
        True if rehash is recommended
    """
    return pwd_context.needs_update(hashed_password)


# =============================================================================
# JWT Token Management
# =============================================================================

class TokenData:
    """Container for decoded JWT token data."""
    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        exp: datetime,
        token_type: str = "access"
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.exp = exp
        self.token_type = token_type


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User UUID as string
        email: User email
        role: User role (ADMIN/TEACHER)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16),  # Unique token ID
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: str) -> str:
    """
    Create a JWT refresh token (longer-lived, minimal claims).
    
    Args:
        user_id: User UUID as string
        
    Returns:
        Encoded JWT refresh token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16),
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {type(e).__name__}")
        return None


def verify_access_token(token: str) -> Optional[TokenData]:
    """
    Verify an access token and return token data.
    
    Args:
        token: JWT access token
        
    Returns:
        TokenData if valid, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != "access":
        logger.warning("Token type mismatch: expected 'access'")
        return None
    
    try:
        return TokenData(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            token_type="access"
        )
    except KeyError as e:
        logger.warning(f"Missing token claim: {e}")
        return None


# =============================================================================
# Canvas Token Encryption (AES-256 via Fernet)
# =============================================================================

def get_fernet() -> Fernet:
    """Get Fernet cipher instance for encryption/decryption."""
    # Ensure key is properly formatted for Fernet
    key = settings.ENCRYPTION_KEY
    if len(key) == 32:
        # Convert 32-byte key to base64 for Fernet
        key = base64.urlsafe_b64encode(key.encode()).decode()
    return Fernet(key.encode())


def encrypt_token(plain_token: str) -> str:
    """
    Encrypt a Canvas access token for secure storage.
    
    Args:
        plain_token: Plain text Canvas access token
        
    Returns:
        Base64-encoded encrypted token
        
    Security Note:
        - Uses Fernet (AES-128-CBC with HMAC)
        - Includes timestamp for optional rotation
        - NEVER log the plain_token value
    """
    fernet = get_fernet()
    encrypted = fernet.encrypt(plain_token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a stored Canvas access token.
    
    Args:
        encrypted_token: Base64-encoded encrypted token
        
    Returns:
        Plain text Canvas access token
        
    Security Note:
        - NEVER log the return value
        - Handle decryption errors gracefully
    """
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()


# =============================================================================
# Utility Functions
# =============================================================================

def generate_secret_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure secret key.
    
    Args:
        length: Key length in bytes
        
    Returns:
        URL-safe base64-encoded key
    """
    return secrets.token_urlsafe(length)


def generate_fernet_key() -> str:
    """
    Generate a valid Fernet encryption key.
    
    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    return Fernet.generate_key().decode()
