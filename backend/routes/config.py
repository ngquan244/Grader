"""
Configuration API routes - App Settings and Role Management
"""
import logging
from fastapi import APIRouter

from backend.schemas import RoleUpdate, ConfigResponse, ModelConfig
from backend.config import settings
from backend.core import BadRequestException, Role, Messages
from src.config import Config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """Get current application configuration"""
    return ConfigResponse(
        role=Config.get_role(),
        available_models=settings.AVAILABLE_MODELS,
        default_model=settings.DEFAULT_MODEL,
        max_iterations=settings.MAX_ITERATIONS
    )


@router.get("/role")
async def get_role():
    """Get current user role"""
    return {"role": Config.get_role()}


@router.post("/role")
async def set_role(request: RoleUpdate):
    """Set user role (STUDENT or TEACHER)"""
    normalized_role = request.role.upper()
    
    if normalized_role not in [Role.STUDENT.value, Role.TEACHER.value]:
        raise BadRequestException(
            f"Vai trò không hợp lệ. Chỉ chấp nhận: {Role.STUDENT.value}, {Role.TEACHER.value}"
        )
    
    Config.set_role(normalized_role)
    
    return {
        "success": True,
        "role": Config.get_role(),
        "message": f"Đã chuyển sang vai trò: {normalized_role}"
    }


@router.post("/switch-role")
async def switch_role():
    """Toggle between STUDENT and TEACHER roles"""
    current = Config.get_role()
    new_role = Role.TEACHER.value if current == Role.STUDENT.value else Role.STUDENT.value
    
    Config.set_role(new_role)
    
    return {
        "success": True,
        "previous_role": current,
        "current_role": new_role,
        "message": f"Đã chuyển từ {current} sang {new_role}"
    }


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
