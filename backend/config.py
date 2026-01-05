"""
Configuration settings for FastAPI backend
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application settings using pydantic-settings"""
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    EXPORTS_DIR: Path = PROJECT_ROOT / "exports"
    QUIZ_DIR: Path = PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
    
    # AI Model settings
    DEFAULT_MODEL: str = "llama3.1:latest"
    AVAILABLE_MODELS: List[str] = [
        "llama3.1:latest",
        "phi3:latest",
        "mistral:latest",
        "gemma2:latest"
    ]
    MAX_ITERATIONS: int = 10
    TEMPERATURE: float = 0.3
    
    # Email settings
    EMAIL_RECEIVER: str = "22028171@vnu.edu.vn"
    EMAIL_USER: str = "testcgvhehe@gmail.com"
    EMAIL_PASSWORD: str = "ksxk vruc fdpc yzjz"
    
    # Database settings
    SQL_SERVER_CONN_STR: str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=244-NGUYEN-QUAN\\SQL2022;"
        "Database=AI_Agent;"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
    )
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.QUIZ_DIR.mkdir(parents=True, exist_ok=True)
