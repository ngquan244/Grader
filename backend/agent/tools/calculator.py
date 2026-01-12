"""
Calculator Tool
Simple mathematical calculation tool for the Teaching Assistant agent.
"""

import json
from typing import Type, ClassVar, Set

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

__all__ = ["CalculatorTool", "CalculatorInput"]


class CalculatorInput(BaseModel):
    """Input schema for calculator tool"""
    expression: str = Field(
        description="Biểu thức toán học cần tính, ví dụ: '2 + 2' hoặc '10 * 5'"
    )


class CalculatorTool(BaseTool):
    """
    Tool để tính toán các phép toán đơn giản.
    
    Supports basic arithmetic operations: +, -, *, /, %, ()
    """
    
    name: str = "calculator"
    description: str = """
    Công cụ tính toán toán học.
    Sử dụng khi người dùng muốn tính toán số học.
    Input: biểu thức toán học (string)
    Ví dụ: '2 + 2', '10 * 5 + 3', '100 / 4'
    """
    args_schema: Type[BaseModel] = CalculatorInput
    
    # Allowed characters for safe evaluation (ClassVar to avoid Pydantic field)
    ALLOWED_CHARS: ClassVar[Set[str]] = set("0123456789+-*/().% ")
    
    def _run(self, expression: str) -> str:
        """
        Execute calculator with the given expression.
        
        Args:
            expression: Mathematical expression to evaluate
            
        Returns:
            JSON string with result or error
        """
        try:
            # Validate expression contains only allowed characters
            if not all(c in self.ALLOWED_CHARS for c in expression):
                return json.dumps({
                    "error": "Biểu thức chứa ký tự không hợp lệ",
                    "allowed": "Chỉ được dùng: 0-9, +, -, *, /, (, ), %, space"
                }, ensure_ascii=False)
            
            # Evaluate expression safely
            result = eval(expression)
            
            return json.dumps({
                "expression": expression,
                "result": result
            }, ensure_ascii=False)
            
        except ZeroDivisionError:
            return json.dumps({
                "error": "Không thể chia cho 0",
                "expression": expression
            }, ensure_ascii=False)
        except SyntaxError:
            return json.dumps({
                "error": "Biểu thức không hợp lệ",
                "expression": expression
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "expression": expression
            }, ensure_ascii=False)
    
    async def _arun(self, expression: str) -> str:
        """Execute tool asynchronously"""
        return self._run(expression)
