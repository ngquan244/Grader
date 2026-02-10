"""
Pydantic schemas for authentication endpoints.
Ensures proper validation and serialization.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# =============================================================================
# Enums (mirror database enums)
# =============================================================================

class UserRoleSchema(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"


class UserStatusSchema(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    PENDING = "PENDING"


class TokenTypeSchema(str, Enum):
    PAT = "PAT"
    OAUTH = "OAUTH"


# =============================================================================
# Request Schemas
# =============================================================================

class SignupRequest(BaseModel):
    """Request schema for user signup."""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User display name")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    canvas_access_token: Optional[str] = Field(None, description="Canvas LMS access token")
    canvas_domain: str = Field(
        default="https://canvas.instructure.com",
        description="Canvas LMS domain URL"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Basic password strength validation."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
    
    @field_validator("canvas_domain")
    @classmethod
    def validate_canvas_domain(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("Canvas domain must use HTTPS")
        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str = Field(..., description="JWT refresh token")


class AddCanvasTokenRequest(BaseModel):
    """Request schema for adding a Canvas token."""
    canvas_domain: str = Field(..., description="Canvas LMS domain URL")
    access_token: str = Field(..., description="Canvas access token")
    token_type: TokenTypeSchema = Field(default=TokenTypeSchema.PAT)
    label: Optional[str] = Field(None, max_length=100, description="Token label")
    
    @field_validator("canvas_domain")
    @classmethod
    def validate_canvas_domain(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("Canvas domain must use HTTPS")
        return v


# =============================================================================
# Response Schemas
# =============================================================================

class UserResponse(BaseModel):
    """Safe user response (no sensitive data)."""
    id: UUID
    email: str
    name: str
    role: UserRoleSchema
    status: UserStatusSchema
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration in seconds")


class LoginResponse(BaseModel):
    """Login response with user and tokens."""
    user: UserResponse
    tokens: AuthTokenResponse


class SignupResponse(BaseModel):
    """Signup response with user and tokens."""
    user: UserResponse
    tokens: AuthTokenResponse
    message: str = "Account created successfully"


class CanvasTokenResponse(BaseModel):
    """Canvas token response (no actual token value)."""
    id: UUID
    canvas_domain: str
    token_type: TokenTypeSchema
    label: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


class DecryptedCanvasTokenResponse(BaseModel):
    """Decrypted Canvas token for API calls."""
    access_token: str = Field(..., description="Decrypted Canvas access token")
    canvas_domain: str = Field(..., description="Canvas LMS domain URL")


class UserProfileResponse(BaseModel):
    """User profile with Canvas tokens."""
    user: UserResponse
    canvas_tokens: List[CanvasTokenResponse] = []


# =============================================================================
# Error Schemas
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: str


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    loc: List[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    success: bool = False
    error: str = "Validation error"
    error_code: str = "VALIDATION_ERROR"
    details: List[ValidationErrorDetail]
