"""
Authentication service for user management.
Handles signup, login, and token operations.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import User, CanvasToken, UserRole, UserStatus, TokenType
from backend.core.security import (
    hash_password,
    verify_password,
    needs_rehash,
    create_access_token,
    create_refresh_token,
    encrypt_token,
    decrypt_token,
)
from backend.core.exceptions import (
    BadRequestException,
    UnauthorizedException,
    NotFoundException,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service with secure password handling and token management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def signup(
        self,
        email: str,
        name: str,
        password: str,
        canvas_access_token: Optional[str] = None,
        canvas_domain: str = "https://canvas.instructure.com",
        role: UserRole = UserRole.TEACHER,
    ) -> User:
        """
        Create a new user account.
        
        Args:
            email: User email (must be unique)
            name: User display name
            password: Plain text password (will be hashed)
            canvas_access_token: Optional Canvas LMS access token
            canvas_domain: Canvas LMS domain
            role: User role (default: TEACHER)
            
        Returns:
            Created User object
            
        Raises:
            BadRequestException: If email already exists
        """
        # Check for existing user
        existing = await self.get_user_by_email(email)
        if existing:
            logger.warning(f"Signup attempt with existing email: {email}")
            raise BadRequestException(
                detail="Email already registered",
                error_code="EMAIL_EXISTS"
            )
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user = User(
            email=email.lower().strip(),
            name=name.strip(),
            password_hash=password_hash,
            role=role,
            status=UserStatus.ACTIVE,
        )
        
        self.db.add(user)
        await self.db.flush()  # Get user.id before creating token
        
        # Create Canvas token if provided
        if canvas_access_token:
            encrypted = encrypt_token(canvas_access_token)
            canvas_token = CanvasToken(
                user_id=user.id,
                canvas_domain=canvas_domain.strip(),
                access_token_encrypted=encrypted,
                token_type=TokenType.PAT,
                label="Primary Canvas Account",
            )
            self.db.add(canvas_token)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"User created: {user.id} ({user.email})")
        return user
    
    async def login(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        """
        Authenticate user and issue tokens.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            UnauthorizedException: If credentials are invalid
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            logger.warning(f"Login attempt for non-existent email: {email}")
            raise UnauthorizedException(
                detail="Invalid email or password",
                error_code="INVALID_CREDENTIALS"
            )
        
        if not user.password_hash:
            logger.warning(f"Login attempt for OAuth-only user: {email}")
            raise UnauthorizedException(
                detail="This account uses OAuth login",
                error_code="OAUTH_ONLY"
            )
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for user: {email}")
            raise UnauthorizedException(
                detail="Invalid email or password",
                error_code="INVALID_CREDENTIALS"
            )
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            raise UnauthorizedException(
                detail="Account is disabled",
                error_code="ACCOUNT_DISABLED"
            )
        
        # Check if password needs rehash (algorithm upgrade)
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            logger.info(f"Password rehashed for user: {user.id}")
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        # Generate tokens
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )
        refresh_token = create_refresh_token(str(user.id))
        
        logger.info(f"User logged in: {user.id}")
        return user, access_token, refresh_token
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()
    
    async def get_active_canvas_tokens(self, user_id: UUID) -> list[CanvasToken]:
        """Get all active (non-revoked) Canvas tokens for a user."""
        result = await self.db.execute(
            select(CanvasToken)
            .where(CanvasToken.user_id == user_id)
            .where(CanvasToken.revoked_at.is_(None))
        )
        return list(result.scalars().all())
    
    async def get_decrypted_canvas_token(
        self,
        user_id: UUID,
        canvas_domain: Optional[str] = None
    ) -> Optional[str]:
        """
        Get decrypted Canvas access token for a user.
        
        Args:
            user_id: User ID
            canvas_domain: Optional domain filter
            
        Returns:
            Decrypted access token or None
            
        Security Note:
            NEVER log the return value
        """
        query = (
            select(CanvasToken)
            .where(CanvasToken.user_id == user_id)
            .where(CanvasToken.revoked_at.is_(None))
        )
        
        if canvas_domain:
            query = query.where(CanvasToken.canvas_domain == canvas_domain)
        
        query = query.order_by(CanvasToken.created_at.desc()).limit(1)
        
        result = await self.db.execute(query)
        token = result.scalar_one_or_none()
        
        if not token:
            return None
        
        # Update last used timestamp
        token.update_last_used()
        await self.db.commit()
        
        return decrypt_token(token.access_token_encrypted)
    
    async def add_canvas_token(
        self,
        user_id: UUID,
        canvas_domain: str,
        access_token: str,
        token_type: TokenType = TokenType.PAT,
        label: Optional[str] = None,
    ) -> CanvasToken:
        """Add a new Canvas token for a user."""
        encrypted = encrypt_token(access_token)
        
        token = CanvasToken(
            user_id=user_id,
            canvas_domain=canvas_domain.strip(),
            access_token_encrypted=encrypted,
            token_type=token_type,
            label=label,
        )
        
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        
        logger.info(f"Canvas token added for user: {user_id}")
        return token
    
    async def revoke_canvas_token(self, token_id: UUID, user_id: UUID) -> bool:
        """Revoke a Canvas token (soft delete)."""
        result = await self.db.execute(
            select(CanvasToken)
            .where(CanvasToken.id == token_id)
            .where(CanvasToken.user_id == user_id)
        )
        token = result.scalar_one_or_none()
        
        if not token:
            return False
        
        token.revoke()
        await self.db.commit()
        
        logger.info(f"Canvas token revoked: {token_id}")
        return True
