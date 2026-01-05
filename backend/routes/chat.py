"""
Chat API routes
Handles AI agent chat interactions
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import ChatRequest, ChatResponse, ChatMessage, ToolUsage
from src.agent_graph import create_agent

router = APIRouter()

# Agent instance cache
_agent_cache = {}


def get_or_create_agent(model: str, max_iterations: int):
    """Lazy initialization of agent with caching"""
    cache_key = f"{model}_{max_iterations}"
    if cache_key not in _agent_cache:
        _agent_cache[cache_key] = create_agent(model=model, max_iterations=max_iterations)
    return _agent_cache[cache_key]


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the AI agent and get response
    """
    try:
        if not request.message.strip():
            return ChatResponse(
                response="Vui lòng nhập tin nhắn",
                success=False,
                error="Empty message"
            )
        
        # Get or create agent
        agent = get_or_create_agent(request.model, request.max_iterations)
        
        # Convert history format
        agent_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]
        
        # Invoke agent
        result = agent.invoke(request.message, agent_history)
        
        # Format tools used
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_available_models():
    """Get list of available AI models"""
    from backend.config import settings
    return {
        "models": settings.AVAILABLE_MODELS,
        "default": settings.DEFAULT_MODEL
    }


@router.delete("/history")
async def clear_history():
    """Clear chat history (handled client-side, this is just for API completeness)"""
    return {"message": "Chat history cleared", "success": True}
