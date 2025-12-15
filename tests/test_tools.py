"""
Unit tests for tools module
"""
import pytest
import json
from src.tools import get_all_tools, get_tool_by_name, CalculatorTool


class TestTools:
    """Test cases for tools"""
    
    def test_get_all_tools(self):
        """Test getting all available tools"""
        tools = get_all_tools()
        assert len(tools) > 0
        assert all(hasattr(tool, 'name') for tool in tools)
        assert all(hasattr(tool, 'description') for tool in tools)
    
    def test_get_tool_by_name(self):
        """Test getting tool by name"""
        tool = get_tool_by_name("calculator")
        assert tool is not None
        assert tool.name == "calculator"
        
        # Test non-existent tool
        tool = get_tool_by_name("non_existent_tool")
        assert tool is None


class TestCalculatorTool:
    """Test cases for Calculator tool"""
    
    def test_calculator_basic(self):
        """Test basic calculator operations"""
        calc = CalculatorTool()
        
        # Addition
        result = calc._run("2 + 2")
        data = json.loads(result)
        assert data["result"] == 4
        
        # Multiplication
        result = calc._run("5 * 3")
        data = json.loads(result)
        assert data["result"] == 15
        
        # Complex expression
        result = calc._run("(10 + 5) * 2")
        data = json.loads(result)
        assert data["result"] == 30
    
    def test_calculator_invalid_input(self):
        """Test calculator with invalid input"""
        calc = CalculatorTool()
        
        # Invalid characters
        result = calc._run("2 + abc")
        data = json.loads(result)
        assert "error" in data
    
    def test_calculator_security(self):
        """Test calculator security (no code execution)"""
        calc = CalculatorTool()
        
        # Try to inject code
        result = calc._run("__import__('os').system('ls')")
        data = json.loads(result)
        assert "error" in data


class TestKaggleTool:
    """Test cases for Kaggle tool"""
    
    @pytest.mark.skip(reason="Requires Kaggle credentials")
    def test_kaggle_score_tool(self):
        """Test Kaggle score tool"""
        tool = get_tool_by_name("get_kaggle_score")
        assert tool is not None
        
        result = tool._run()
        # Should return JSON with score data
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
