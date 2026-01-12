"""
Agent module for the Teaching Assistant Grader.
Contains AI agent, tools, and grading functionality.
"""

from .agent_graph import ReActAgent
from .tools import (
    get_all_tools, 
    get_tool_by_name,
    get_grading_tool,
    get_role,
    set_role,
    check_role,
    CalculatorTool,
    QuizGeneratorTool,
    ExamResultSummaryTool,
    GradingTool,
)

__all__ = [
    "ReActAgent",
    "get_all_tools",
    "get_tool_by_name",
    "get_grading_tool",
    "get_role",
    "set_role",
    "check_role",
    "CalculatorTool",
    "QuizGeneratorTool", 
    "ExamResultSummaryTool",
    "GradingTool",
]
