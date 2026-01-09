"""
Agent Tools Package
Contains all tools for the Teaching Assistant Grader agent.

Each tool is in its own module for better maintainability and extensibility.
"""

from .base import (
    get_role,
    set_role,
    check_role,
    require_role,
    ROLE_FILE,
)
from .calculator import CalculatorTool
from .quiz_generator import QuizGeneratorTool
from .exam_summary import ExamResultSummaryTool
from .grading import GradingTool, get_grading_tool

from langchain.tools import BaseTool
from typing import Optional, List


def get_all_tools() -> List[BaseTool]:
    """Return list of all available tools"""
    return [
        get_grading_tool(),
        CalculatorTool(),
        QuizGeneratorTool(),
        ExamResultSummaryTool(),
    ]


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """Get a tool by its name"""
    tools = get_all_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None


__all__ = [
    # Role management
    "get_role",
    "set_role", 
    "check_role",
    "require_role",
    "ROLE_FILE",
    # Tools
    "CalculatorTool",
    "QuizGeneratorTool",
    "ExamResultSummaryTool",
    "GradingTool",
    "get_grading_tool",
    # Utility functions
    "get_all_tools",
    "get_tool_by_name",
]
