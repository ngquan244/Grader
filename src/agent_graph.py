"""
LangGraph ReAct Agent Implementation
AI Agent mạnh mẽ với khả năng reasoning, planning và tool calling
"""
import json
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from .tools import get_all_tools


# Define Agent State
class AgentState(TypedDict):
    """State của agent trong graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_action: str  # "continue", "end", "error"
    iteration_count: int  # Đếm số lần lặp để tránh infinite loop
    max_iterations: int  # Giới hạn số lần lặp


class ReActAgent:
    """
    ReAct Agent implementation using LangGraph
    
    Features:
    - Multi-step reasoning
    - Tool calling with validation
    - Error handling & retry logic
    - Memory management
    - Self-reflection
    """
    
    def __init__(
        self,
        model_name: str = "llama3.1:latest",
        max_iterations: int = 10,
        temperature: float = 0.7
    ):
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.temperature = temperature
        
        # Initialize LLM
        self.llm = ChatOllama(
            model=model_name,
            temperature=temperature,
        )
        
        # Get tools
        self.tools = get_all_tools()
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _create_system_prompt(self) -> str:
        """Tạo system prompt cho agent"""
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        return f"""Bạn là một AI Agent thông minh sử dụng ReAct pattern (Reasoning + Acting).

**Available Tools:**
{tool_descriptions}

**Your Capabilities:**
1. Phân tích yêu cầu người dùng một cách sâu sắc
2. Lập kế hoạch nhiều bước để giải quyết vấn đề phức tạp
3. Sử dụng tools khi cần thiết
4. Tự đánh giá và điều chỉnh hành động
5. Xử lý lỗi và thử lại khi cần

**Instructions:**
- Suy nghĩ từng bước một (step-by-step reasoning)
- Giải thích lý do tại sao bạn chọn tool cụ thể
- Nếu tool trả về lỗi, hãy phân tích và thử cách khác
- Khi hoàn thành, đưa ra câu trả lời rõ ràng và hữu ích
- Luôn lịch sự, chính xác và súc tích

**QUAN TRỌNG - Khi nào sử dụng tools:**
- CHỈ sử dụng execute_notebook tool KHI người dùng YÊU CẦU RÕ RÀNG:
  + "Chấm bài", "chấm điểm", "kiểm tra bài thi"
  + "Xem kết quả", "tính điểm"
  + "Grade the exam", "check the answers"
- KHÔNG tự động chạy notebook khi:
  + Người dùng chỉ chào hỏi: "xin chào", "hello", "hi"
  + Hỏi thông tin chung
  + Chat thông thường
- Với câu hỏi thông thường, trả lời trực tiếp KHÔNG cần tool

**Khi tạo quiz (quiz_generator tool):**
- CHỈ sử dụng KHI được yêu cầu: "tạo quiz", "gen quiz", "tạo đề thi"
- Tool sẽ tự động đọc PDF từ data/quiz/ và tạo file HTML
- Kết quả trả về có field "file_url" với đường dẫn file:///
- HÃY HIỂN THỊ RÕ RÀNG:
  + Link quiz (file_url) để sinh viên có thể copy-paste vào browser
  + Hướng dẫn: "Copy link này và dán vào trình duyệt để mở quiz"
  + Số câu hỏi đã tạo và file HTML path
- Định dạng output dễ đọc, BẮT BUỘC hiển thị URL đầy đủ

**Khi chấm điểm bài thi:**
- Sử dụng tool execute_notebook để chạy notebook
- Tool sẽ trả về JSON với thông tin đầy đủ
- HÃY TRÍCH XUẤT VÀ HIỂN THỊ ĐẦY ĐỦ:
  + Thông tin sinh viên: student_id, name, email
  + Kết quả: total_questions, correct, wrong, blank, score
  + Exam code và student code
- Định dạng câu trả lời dễ đọc, rõ ràng

**Khi có lỗi xử lý ảnh:**
- Notebook sẽ trả về error với suggestion
- HÃY GIẢI THÍCH RÕ RÀNG cho user:
  + Lỗi gì đã xảy ra (timing marks không đủ, warp thất bại, cells không đủ...)
  + Nguyên nhân có thể: ảnh mờ, nghiêng, ánh sáng kém
  + Hướng dẫn: chụp lại ảnh rõ nét, ánh sáng đủ, không bị lóa
- KHÔNG chỉ copy error message, hãy dịch sang tiếng Việt dễ hiểu

**ReAct Pattern:**
1. Thought: Suy nghĩ về vấn đề
2. Action: Chọn tool và thực thi
3. Observation: Quan sát kết quả
4. Reflection: Đánh giá và quyết định bước tiếp theo
"""
    
    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """
        Quyết định xem agent nên tiếp tục hay kết thúc
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # Kiểm tra giới hạn iteration
        if state["iteration_count"] >= state["max_iterations"]:
            return "end"
        
        # Nếu message cuối có tool calls, tiếp tục
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        
        # Nếu không, kết thúc
        return "end"
    
    def _call_model(self, state: AgentState) -> dict:
        """
        Gọi LLM với context và tools
        """
        messages = state["messages"]
        
        # Thêm system message nếu chưa có
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(content=self._create_system_prompt())
            messages = [system_msg] + list(messages)
        
        # Call LLM
        response = self.llm_with_tools.invoke(messages)
        
        # Tăng iteration count
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1
        }
    
    def _build_graph(self) -> StateGraph:
        """
        Xây dựng StateGraph cho agent
        
        Flow:
        START -> agent -> [tools | END]
        tools -> agent (loop back for reflection)
        """
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        # Add edge from tools back to agent for reflection
        workflow.add_edge("tools", "agent")
        
        # Compile
        return workflow.compile()
    
    def invoke(self, user_input: str, history: list[dict] = None) -> dict:
        """
        Thực thi agent với user input
        
        Args:
            user_input: Câu hỏi/yêu cầu của user
            history: Lịch sử chat (optional)
        
        Returns:
            dict với response và metadata
        """
        # Prepare messages
        messages = []
        
        # Add history if provided
        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # Add current user input
        messages.append(HumanMessage(content=user_input))
        
        # Create initial state
        initial_state = {
            "messages": messages,
            "next_action": "continue",
            "iteration_count": 0,
            "max_iterations": self.max_iterations
        }
        
        # Run graph
        try:
            result = self.graph.invoke(initial_state)
            
            # Extract response
            last_message = result["messages"][-1]
            
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            else:
                response_content = str(last_message)
            
            # Extract tool calls info for debugging
            tool_calls_info = []
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                    if msg.tool_calls:
                        tool_calls_info.extend([
                            {
                                "tool": tc["name"],
                                "args": tc.get("args", {})
                            }
                            for tc in msg.tool_calls
                        ])
            
            return {
                "response": response_content,
                "iterations": result["iteration_count"],
                "tools_used": tool_calls_info,
                "success": True
            }
        
        except Exception as e:
            return {
                "response": f"❌ Lỗi: {str(e)}",
                "error": str(e),
                "success": False
            }
    
    def stream(self, user_input: str, history: list[dict] = None):
        """
        Stream agent execution (for real-time UI updates)
        """
        # Prepare messages
        messages = []
        
        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_input))
        
        # Create initial state
        initial_state = {
            "messages": messages,
            "next_action": "continue",
            "iteration_count": 0,
            "max_iterations": self.max_iterations
        }
        
        # Stream execution
        for output in self.graph.stream(initial_state):
            yield output


# Factory function
def create_agent(model: str = "llama3.1:latest", max_iterations: int = 10) -> ReActAgent:
    """Factory function để tạo agent"""
    return ReActAgent(model_name=model, max_iterations=max_iterations)


# Test function
if __name__ == "__main__":
    # Test agent
    agent = create_agent()
    
    test_queries = [
        "Xin chào!",
        "Cho tôi điểm Kaggle",
        "Tính 25 * 4 + 10",
        "Giải thích machine learning là gì?"
    ]
    
    print("🚀 Testing ReAct Agent\n")
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"User: {query}")
        print(f"{'='*60}")
        
        result = agent.invoke(query)
        
        print(f"\n Agent: {result['response']}")
        print(f"\n Metadata:")
        print(f"  - Iterations: {result.get('iterations', 0)}")
        print(f"  - Tools used: {result.get('tools_used', [])}")
        print(f"  - Success: {result.get('success', False)}")
