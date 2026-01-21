"""
Configuration API routes - App Settings
"""
import logging
from fastapi import APIRouter

from backend.schemas import ConfigResponse, ModelConfig
from backend.config import settings
from backend.core import BadRequestException, Messages

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """Get current application configuration"""
    return ConfigResponse(
        available_models=settings.AVAILABLE_MODELS,
        default_model=settings.DEFAULT_MODEL,
        max_iterations=settings.MAX_ITERATIONS
    )


@router.get("/models")
async def get_models():
    """Get available AI models"""
    return {
        "models": settings.AVAILABLE_MODELS,
        "default": settings.DEFAULT_MODEL
    }


@router.post("/model")
async def set_model(config: ModelConfig):
    """Set AI model configuration (for session)"""
    if config.model not in settings.AVAILABLE_MODELS:
        raise BadRequestException(
            f"Model không hợp lệ. Các model có sẵn: {', '.join(settings.AVAILABLE_MODELS)}"
        )
    
    return {
        "success": True,
        "model": config.model,
        "max_iterations": config.max_iterations,
        "message": f"Đã cấu hình model: {config.model}"
    }
