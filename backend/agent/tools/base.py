"""
Base utilities for agent tools.
Contains shared functionality like role management and common helpers.
"""

import logging
from pathlib import Path
from typing import Callable
from functools import wraps

from ...config import settings
from ...core.logger import logger

__all__ = [
    "get_role",
    "set_role", 
    "check_role",
    "require_role",
    "ROLE_FILE",
    "logger",
]


# Role management
ROLE_FILE = settings.PROJECT_ROOT / "role.txt"
_ROLE = None


def get_role() -> str:
    """
    Get current role from file, fallback to default.
    
    Returns:
        str: Current role ('STUDENT' or 'TEACHER')
    """
    global _ROLE
    if _ROLE is not None:
        return _ROLE
    
    if ROLE_FILE.exists():
        try:
            with open(ROLE_FILE, 'r', encoding='utf-8') as f:
                role = f.read().strip().upper()
                if role in ("STUDENT", "TEACHER"):
                    _ROLE = role
                    return role
        except Exception:
            pass
    
    _ROLE = "STUDENT"
    return _ROLE


def set_role(role: str) -> None:
    """
    Set current role and persist to file.
    
    Args:
        role: Role to set ('STUDENT' or 'TEACHER')
        
    Raises:
        ValueError: If role is not valid
    """
    global _ROLE
    role = role.upper()
    
    if role not in ("STUDENT", "TEACHER"):
        raise ValueError("Role must be 'STUDENT' or 'TEACHER'")
    
    with open(ROLE_FILE, 'w', encoding='utf-8') as f:
        f.write(role)
    
    _ROLE = role


def check_role(role_required: str) -> bool:
    """
    Check if current role matches the required role.
    
    Args:
        role_required: The role required to perform the action
        
    Returns:
        bool: True if role matches, False otherwise
    """
    actual_role = get_role()
    if (actual_role or "").lower() != role_required.lower():
        logger.warning(
            f"Access denied. Required role: {role_required}, actual role: {actual_role}"
        )
        return False
    return True


def require_role(role_required: str):
    """
    Decorator to require a specific role for a function.
    
    Args:
        role_required: The role required to execute the function
        
    Returns:
        Decorated function that checks role before execution
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_role(role_required):
                actual_role = get_role()
                raise PermissionError(
                    f"Access denied. Required role: {role_required}, "
                    f"actual role: {actual_role}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def format_permission_error(required_role: str) -> dict:
    """
    Format a standard permission error response.
    
    Args:
        required_role: The role that was required
        
    Returns:
        dict: Formatted error response
    """
    actual_role = get_role()
    return {
        "error": f"Chỉ {required_role} mới có quyền thực hiện chức năng này",
        "fatal": True,
        "required_role": required_role,
        "your_role": actual_role,
        "message": (
            f"Bạn không có quyền thực hiện chức năng này. "
            f"Yêu cầu quyền: {required_role}. "
            f"Quyền hiện tại: {actual_role if actual_role else 'Không xác định'}"
        )
    }
