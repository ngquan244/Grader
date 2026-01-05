"""
Configuration API routes
Handles role switching and app configuration
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import RoleUpdate, ConfigResponse, ModelConfig
from backend.config import settings
from src.config import Config

router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    Get current application configuration
    """
    return ConfigResponse(
        role=Config.get_role(),
        available_models=settings.AVAILABLE_MODELS,
        default_model=settings.DEFAULT_MODEL,
        max_iterations=settings.MAX_ITERATIONS
    )


@router.get("/role")
async def get_role():
    """
    Get current user role
    """
    return {"role": Config.get_role()}


@router.post("/role")
async def set_role(request: RoleUpdate):
    """
    Set user role (STUDENT or TEACHER)
    """
    try:
        Config.set_role(request.role.upper())
        return {
            "success": True,
            "role": Config.get_role(),
            "message": f"Đã chuyển sang vai trò: {request.role}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/switch-role")
async def switch_role():
    """
    Toggle between STUDENT and TEACHER roles
    """
    current = Config.get_role()
    new_role = "TEACHER" if current == "STUDENT" else "STUDENT"
    Config.set_role(new_role)
    
    return {
        "success": True,
        "previous_role": current,
        "current_role": new_role,
        "message": f"Đã chuyển từ {current} sang {new_role}"
    }


@router.get("/models")
async def get_models():
    """
    Get available AI models
    """
    return {
        "models": settings.AVAILABLE_MODELS,
        "default": settings.DEFAULT_MODEL
    }


@router.post("/model")
async def set_model(config: ModelConfig):
    """
    Set AI model configuration (for session)
    Note: This is stateless, actual model selection is per-request
    """
    if config.model not in settings.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model không hợp lệ. Các model có sẵn: {', '.join(settings.AVAILABLE_MODELS)}"
        )
    
    return {
        "success": True,
        "model": config.model,
        "max_iterations": config.max_iterations,
        "message": f"Đã cấu hình model: {config.model}"
    }
