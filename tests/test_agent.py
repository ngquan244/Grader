"""
Unit tests for agent_graph module
"""
import pytest
from src.agent_graph import create_agent, ReActAgent


class TestReActAgent:
    """Test cases for ReAct Agent"""
    
    def test_agent_creation(self):
        """Test agent can be created successfully"""
        agent = create_agent()
        assert agent is not None
        assert isinstance(agent, ReActAgent)
    
    def test_agent_with_custom_params(self):
        """Test agent creation with custom parameters"""
        agent = create_agent(model="llama3.1:latest", max_iterations=5)
        assert agent.model_name == "llama3.1:latest"
        assert agent.max_iterations == 5
    
    def test_simple_query(self):
        """Test agent with simple query (no tools)"""
        agent = create_agent()
        result = agent.invoke("Xin chào!")
        assert result is not None
        assert "response" in result
        assert result.get("success") in [True, False]
    
    @pytest.mark.skip(reason="Requires Ollama running")
    def test_tool_calling(self):
        """Test agent can call tools"""
        agent = create_agent()
        result = agent.invoke("Tính 5 + 5")
        assert "tools_used" in result
        assert len(result.get("tools_used", [])) > 0


class TestAgentState:
    """Test agent state management"""
    
    def test_iteration_limit(self):
        """Test that agent respects iteration limit"""
        agent = create_agent(max_iterations=2)
        # This should stop after max iterations
        result = agent.invoke("Test iteration limit")
        assert result.get("iterations", 0) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
