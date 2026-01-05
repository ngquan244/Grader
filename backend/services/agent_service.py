"""
AI Agent Service
Handles AI model interactions and agent management
"""
import logging
from typing import Dict, List, Optional, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing AI agents"""
    
    _instance: Optional["AgentService"] = None
    _agent_cache: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_agent(self, model: str, max_iterations: int):
        """Get or create an agent instance"""
        cache_key = f"{model}_{max_iterations}"
        
        if cache_key not in self._agent_cache:
            logger.info(f"Creating new agent: {cache_key}")
            from src.agent_graph import create_agent
            self._agent_cache[cache_key] = create_agent(
                model=model,
                max_iterations=max_iterations
            )
        
        return self._agent_cache[cache_key]
    
    def invoke(
        self,
        message: str,
        history: List[Dict[str, str]],
        model: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """Invoke the AI agent with a message"""
        agent = self.get_agent(model, max_iterations)
        return agent.invoke(message, history)
    
    def clear_cache(self):
        """Clear the agent cache"""
        self._agent_cache.clear()
        logger.info("Agent cache cleared")


# Singleton instance
agent_service = AgentService()
