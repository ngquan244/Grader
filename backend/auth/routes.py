"""
Authentication API routes.
Handles signup, login, and user profile endpoints.
"""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.auth_service import AuthService
from backend.core.config import settings
from backend.auth.schemas import (
    SignupRequest,
    SignupResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    UserProfileResponse,
    AuthTokenResponse,
    CanvasTokenResponse,
    AddCanvasTokenRequest,
    DecryptedCanvasTokenResponse,
)
from backend.auth.dependencies import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Create a new user account with email/password authentication. "
                "Optionally provide a Canvas LMS access token.",
)
async def signup(
    request: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SignupResponse:
    """
    Register a new user account.
    
    - **email**: User email (must be unique)
    - **name**: User display name
    - **password**: Password (min 8 chars, must include uppercase, lowercase, digit)
    - **canvas_access_token**: Optional Canvas LMS access token
    - **canvas_domain**: Canvas LMS domain (default: canvas.instructure.com)
    """
    auth_service = AuthService(db)
    
    user = await auth_service.signup(
        email=request.email,
        name=request.name,
        password=request.password,
        canvas_access_token=request.canvas_access_token,
        canvas_domain=request.canvas_domain,
    )
    
    # Generate tokens
    _, access_token, refresh_token = await auth_service.login(
        email=request.email,
        password=request.password,
    )
    
    return SignupResponse(
        user=UserResponse.model_validate(user),
        tokens=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        message="Account created successfully",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate user",
    description="Authenticate with email and password. Returns JWT tokens.",
)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """
    Authenticate user and issue JWT tokens.
    
    - **email**: User email address
    - **password**: User password
    """
    auth_service = AuthService(db)
    
    user, access_token, refresh_token = await auth_service.login(
        email=request.email,
        password=request.password,
    )
    
    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get the authenticated user's profile with Canvas tokens.",
)
async def get_current_user_profile(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """
    Get the current user's profile including Canvas tokens.
    
    Requires valid JWT access token in Authorization header.
    """
    auth_service = AuthService(db)
    
    # Get Canvas tokens
    canvas_tokens = await auth_service.get_active_canvas_tokens(current_user.id)
    
    return UserProfileResponse(
        user=UserResponse.model_validate(current_user),
        canvas_tokens=[
            CanvasTokenResponse(
                id=token.id,
                canvas_domain=token.canvas_domain,
                token_type=token.token_type,
                label=token.label,
                created_at=token.created_at,
                last_used_at=token.last_used_at,
                is_active=token.is_active,
            )
            for token in canvas_tokens
        ],
    )


@router.post(
    "/canvas-tokens",
    response_model=CanvasTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Canvas LMS token",
    description="Add a new Canvas LMS access token for the current user.",
)
async def add_canvas_token(
    request: AddCanvasTokenRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CanvasTokenResponse:
    """
    Add a Canvas LMS access token.
    
    - **canvas_domain**: Canvas LMS domain URL
    - **access_token**: Canvas access token (will be encrypted)
    - **token_type**: PAT or OAUTH
    - **label**: Optional friendly label
    """
    auth_service = AuthService(db)
    
    token = await auth_service.add_canvas_token(
        user_id=current_user.id,
        canvas_domain=request.canvas_domain,
        access_token=request.access_token,
        token_type=request.token_type,
        label=request.label,
    )
    
    return CanvasTokenResponse(
        id=token.id,
        canvas_domain=token.canvas_domain,
        token_type=token.token_type,
        label=token.label,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        is_active=token.is_active,
    )


@router.delete(
    "/canvas-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Canvas token",
    description="Revoke (soft delete) a Canvas LMS access token.",
)
async def revoke_canvas_token(
    token_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke a Canvas LMS access token."""
    from uuid import UUID
    from backend.core.exceptions import NotFoundException
    
    auth_service = AuthService(db)
    
    success = await auth_service.revoke_canvas_token(
        token_id=UUID(token_id),
        user_id=current_user.id,
    )
    
    if not success:
        raise NotFoundException(
            detail="Canvas token not found",
            error_code="TOKEN_NOT_FOUND",
        )


@router.get(
    "/canvas-tokens/active",
    response_model=DecryptedCanvasTokenResponse,
    summary="Get active Canvas token (decrypted)",
    description="Get the most recently used active Canvas token for API calls.",
)
async def get_active_canvas_token(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    canvas_domain: Optional[str] = None,
) -> DecryptedCanvasTokenResponse:
    """
    Get decrypted Canvas access token for API calls.
    
    Query params:
        canvas_domain: Optional filter by domain
    """
    from backend.core.exceptions import NotFoundException
    
    auth_service = AuthService(db)
    
    # Get active tokens to find the domain
    tokens = await auth_service.get_active_canvas_tokens(current_user.id)
    
    if not tokens:
        raise NotFoundException(
            detail="No active Canvas token found",
            error_code="NO_CANVAS_TOKEN",
        )
    
    # Use provided domain or get from first token
    domain = canvas_domain or tokens[0].canvas_domain
    
    decrypted = await auth_service.get_decrypted_canvas_token(
        user_id=current_user.id,
        canvas_domain=domain if canvas_domain else None,
    )
    
    if not decrypted:
        raise NotFoundException(
            detail="Canvas token not found or could not be decrypted",
            error_code="TOKEN_DECRYPT_FAILED",
        )
    
    return DecryptedCanvasTokenResponse(
        access_token=decrypted,
        canvas_domain=domain,
    )
