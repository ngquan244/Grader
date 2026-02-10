"""
FastAPI dependencies for authentication and authorization.
Implements role-based access control (RBAC).
"""
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, User, UserRole
from backend.core.security import verify_access_token
from backend.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(
    scheme_name="JWT",
    description="JWT access token for authentication",
    auto_error=True,
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    
    # Verify token
    token_data = verify_access_token(token)
    if token_data is None:
        logger.warning("Invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(UUID(token_data.user_id))
    
    if user is None:
        logger.warning(f"User not found for token: {token_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to ensure user is active.
    This is a convenience wrapper for get_current_user.
    """
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            pass
    
    Args:
        *allowed_roles: Roles allowed to access the endpoint
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.id}: "
                f"role {current_user.role} not in {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    
    return role_checker


# Convenience dependencies for common role checks
RequireAdmin = Depends(require_role(UserRole.ADMIN))
RequireTeacher = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN))


# Type aliases for cleaner function signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
TeacherUser = Annotated[User, Depends(require_role(UserRole.TEACHER, UserRole.ADMIN))]
