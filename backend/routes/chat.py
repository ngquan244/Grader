"""
Chat API routes - AI Agent Chat Interactions
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.database.base import get_async_session
from backend.schemas import ChatRequest, ChatResponse, ToolUsage
from backend.services import agent_service
from backend.services.groq_key_service import get_effective_groq_key
from backend.core.config import settings
from backend.core import Messages, BadRequestException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_async_session),
):
    """Send a message to the AI agent and get response"""
    if not request.message.strip():
        raise BadRequestException(Messages.EMPTY_MESSAGE)

    # Resolve Groq API key: DB > env
    db_groq_key, _source = await get_effective_groq_key(db)

    # Convert history format
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history
    ]

    # Invoke agent with user context
    result = agent_service.invoke(
        message=request.message,
        history=history,
        model=request.model,
        max_iterations=request.max_iterations,
        user_id=str(user.id),
        db_groq_key=db_groq_key,
    )
    
    # Format response
    tools_used = [
        ToolUsage(tool=t.get("tool", ""), args=t.get("args", {}))
        for t in result.get("tools_used", [])
    ]
    
    return ChatResponse(
        response=result.get("response", ""),
        iterations=result.get("iterations", 0),
        tools_used=tools_used,
        success=result.get("success", True)
    )


@router.get("/models")
def get_available_models(user: CurrentUser):
    """Get list of available AI models"""
    return {
        "models": settings.AVAILABLE_MODELS,
        "default": settings.DEFAULT_MODEL,
        "provider": settings.LLM_PROVIDER,
    }


@router.delete("/history")
def clear_history(user: CurrentUser):
    """Clear chat history"""
    return {"message": Messages.HISTORY_CLEARED, "success": True}
