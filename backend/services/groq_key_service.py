"""
Groq API Key Service
====================
System-wide Groq API key management stored encrypted in app_settings.
DB key takes priority over environment variable.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import encrypt_token, decrypt_token
from backend.database.models.invite_code import AppSetting

logger = logging.getLogger(__name__)

_SETTING_KEY = "GROQ_API_KEY"
_GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"


async def get_groq_key_record(db: AsyncSession) -> Optional[AppSetting]:
    """Get the raw AppSetting record for Groq API key."""
    stmt = select(AppSetting).where(AppSetting.key == _SETTING_KEY)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_groq_api_key(db: AsyncSession) -> Optional[str]:
    """
    Read and decrypt the Groq API key from DB.
    Returns None if not stored.
    """
    record = await get_groq_key_record(db)
    if not record or not record.value:
        return None
    encrypted = record.value.get("encrypted")
    if not encrypted:
        return None
    try:
        return decrypt_token(encrypted)
    except Exception:
        logger.error("Failed to decrypt Groq API key from DB")
        return None


async def set_groq_api_key(
    db: AsyncSession,
    plain_key: str,
    updated_by: Optional[str] = None,
) -> None:
    """Encrypt and upsert the Groq API key in app_settings."""
    encrypted = encrypt_token(plain_key)
    value = {
        "encrypted": encrypted,
        "updated_by": updated_by,
        "updated_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    record = await get_groq_key_record(db)
    if record:
        record.value = value
        record.updated_at = datetime.now(timezone.utc)
    else:
        db.add(AppSetting(key=_SETTING_KEY, value=value))
    await db.commit()
    logger.info("Groq API key updated in DB by %s", updated_by or "unknown")


async def delete_groq_api_key(db: AsyncSession) -> bool:
    """Remove the Groq API key from app_settings. Returns True if deleted."""
    record = await get_groq_key_record(db)
    if not record:
        return False
    await db.delete(record)
    await db.commit()
    logger.info("Groq API key removed from DB")
    return True


async def validate_groq_api_key(plain_key: str) -> bool:
    """
    Test a Groq API key by calling the models endpoint.
    Returns True if the key is valid.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _GROQ_MODELS_URL,
                headers={"Authorization": f"Bearer {plain_key}"},
            )
        return resp.status_code == 200
    except Exception:
        logger.warning("Groq API key validation failed (network error)")
        return False


def mask_key(plain_key: str) -> str:
    """Mask an API key for display: gsk_ab...xyz"""
    if len(plain_key) <= 8:
        return "***"
    return f"{plain_key[:6]}...{plain_key[-4:]}"


async def get_effective_groq_key(db: AsyncSession) -> tuple[Optional[str], str]:
    """
    Get the effective Groq API key checking DB first, then env var.
    Returns (key_or_none, source) where source is "db" | "env" | "none".
    """
    db_key = await get_groq_api_key(db)
    if db_key:
        return db_key, "db"

    from backend.core.config import settings
    env_key = settings.GROQ_API_KEY
    if env_key and env_key.strip():
        return env_key, "env"

    return None, "none"
