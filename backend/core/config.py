"""
Core application configuration with security-first design.
Loads all settings from environment variables.
"""
import warnings
from functools import lru_cache
from typing import List, Optional
from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Development-only default keys (DO NOT USE IN PRODUCTION)
_DEV_JWT_SECRET = "dev-only-secret-key-change-in-production-min-32-chars"
_DEV_ENCRYPTION_KEY = "dev-only-encryption-key-32chars!"  # Must be 32 chars for Fernet


class Settings(BaseSettings):
    """
    Application settings using pydantic-settings.
    All sensitive values MUST come from environment variables in production.
    """
    
    # ==========================================================================
    # Server Configuration
    # ==========================================================================
    HOST: str = "0.0.0.0"  # Bind to all interfaces
    PORT: int = 8000  # Default port (8000 often conflicted with other services)
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production
    
    # ==========================================================================
    # CORS Configuration
    # ==========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    
    # ==========================================================================
    # Database Configuration (PostgreSQL)
    # ==========================================================================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "grader_user"
    POSTGRES_PASSWORD: str = "grader_secret_password"  # Same as docker-compose default
    POSTGRES_DB: str = "grader_db"
    
    @property
    def DATABASE_URL(self) -> str:
        """Async PostgreSQL connection URL for FastAPI."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync PostgreSQL connection URL for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==========================================================================
    # JWT Configuration
    # ==========================================================================
    JWT_SECRET_KEY: str = _DEV_JWT_SECRET  # Override in .env for production
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ==========================================================================
    # Encryption Configuration (for Canvas tokens)
    # ==========================================================================
    ENCRYPTION_KEY: str = _DEV_ENCRYPTION_KEY  # Override in .env for production
    
    # ==========================================================================
    # Password Hashing Configuration
    # ==========================================================================
    PASSWORD_HASH_ALGORITHM: str = "argon2"  # argon2 | bcrypt
    BCRYPT_ROUNDS: int = 12
    
    # ==========================================================================
    # Project Paths (computed from PROJECT_ROOT)
    # ==========================================================================
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    
    @property
    def DATA_DIR(self) -> Path:
        return self.PROJECT_ROOT / "data"
    
    @property
    def LOGS_DIR(self) -> Path:
        return self.PROJECT_ROOT / "logs"
    
    @property
    def EXPORTS_DIR(self) -> Path:
        return self.PROJECT_ROOT / "exports"
    
    @property
    def QUIZ_DIR(self) -> Path:
        return self.PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
    
    @model_validator(mode='after')
    def warn_dev_secrets(self) -> 'Settings':
        """Warn if using development secrets in non-dev environment."""
        if self.ENVIRONMENT != "development":
            if self.JWT_SECRET_KEY == _DEV_JWT_SECRET:
                warnings.warn(
                    "Using development JWT_SECRET_KEY in non-development environment! "
                    "Set JWT_SECRET_KEY in your .env file.",
                    UserWarning
                )
            if self.ENCRYPTION_KEY == _DEV_ENCRYPTION_KEY:
                warnings.warn(
                    "Using development ENCRYPTION_KEY in non-development environment! "
                    "Set ENCRYPTION_KEY in your .env file.",
                    UserWarning
                )
        return self
    
    # ==========================================================================
    # AI Model Configuration (preserved from original)
    # ==========================================================================
    DEFAULT_MODEL: str = "llama3.1:latest"
    AVAILABLE_MODELS: List[str] = [
        "llama3.1:latest",
        "phi3:latest",
        "mistral:latest",
        "gemma2:latest"
    ]
    MAX_ITERATIONS: int = 10
    TEMPERATURE: float = 0.3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use dependency injection in FastAPI routes.
    """
    return Settings()


# Global settings instance
settings = get_settings()
