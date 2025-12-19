import json
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from .tools import get_all_tools


class AgentState(TypedDict):
    """State của agent trong graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_action: str
    iteration_count: int
    max_iterations: int


class ReActAgent:
    """
    ReAct Agent implementation using LangGraph 
    """
    
    def __init__(
        self,
        model_name: str = "llama3.1:latest",
        max_iterations: int = 10,
        temperature: float = 0.3,  
        max_history: int = 5 
    ):
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.MAX_HISTORY = max_history
        
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
        """
         System prompt NGẮN GỌN, RÕ RÀNG, TRÁNH CONFUSION
        """
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        return f"""You are a helpful AI assistant. Answer user questions naturally and accurately.

Available tools:
{tool_descriptions}

Tool usage rules:
- execute_notebook → only when user explicitly asks to "grade exam", "check answers", "chấm bài"
- quiz_generator → only when user explicitly asks to "create quiz", "tạo quiz"
- calculator → only for explicit numeric calculations (e.g., 123 * 456 + 789)
- web_search → only for current events or up-to-date information

Important:
- Always answer greetings, casual chat, compliments naturally, without using tools or apologizing.
- Always answer general knowledge questions (animal sizes, common facts, definitions) directly, without apologizing.
- Only apologize if you truly cannot answer or the data is missing.
- Only use tools when explicitly requested or clearly needed.
- Do not make up numbers or facts. If unsure, say "I don't know".
- For subjective questions, clarify it is opinion-based.

When using tools:
- Extract and display full information from results
- Format output clearly
- Handle errors with helpful explanations

"""
    



    def _summarize_history(self, history_messages: list[BaseMessage]) -> AIMessage:
        """
        Tóm tắt history dài thành 1 message ngắn để giữ context.
        """
        if not history_messages:
            return None

        summary_text = "Tóm tắt lịch sử chat trước đó:\n"
        for msg in history_messages:
            role = "User" if isinstance(msg, HumanMessage) else "AI"
            summary_text += f"{role}: {msg.content}\n"

        return AIMessage(content=summary_text)

    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        messages = state["messages"]
        last_message = messages[-1]
        
        greetings = ["hello", "xin chào", "hi"]
        if isinstance(last_message, AIMessage):
            content_lower = last_message.content.lower()
            if any(greet in content_lower for greet in greetings):
                return "end"
        
        if state["iteration_count"] >= state["max_iterations"]:
            return "end"
        
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        
        return "end"

    def _after_tool(self, state: AgentState) -> Literal["agent", "end"]:
        last_msg = state["messages"][-1]

        if isinstance(last_msg, ToolMessage):
            try:
                data = json.loads(last_msg.content)
                if data.get("fatal") is True or "error" in data:
                    return "end"
            except Exception:
                pass

        return "agent"

    
    def _call_model(self, state: AgentState) -> dict:
        """
        Gọi LLM với context và tools
        """
        messages = state["messages"]
        
        has_system = any(isinstance(msg, SystemMessage) for msg in messages)
        
        if not has_system:
            system_msg = SystemMessage(content=self._create_system_prompt())
            messages = [system_msg] + list(messages)
        
        # Call LLM
        response = self.llm_with_tools.invoke(messages)
        
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1
        }
    
    def _build_graph(self) -> StateGraph:
        """Xây dựng StateGraph cho agent"""
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
        
        # Add edge from tools back to agent
        workflow.add_conditional_edges(
            "tools",
            self._after_tool,
            {
                "agent": "agent",
                "end": END
            }
        )

        return workflow.compile()
    
    def _extract_text_from_content(self, content) -> str:
        """
        Extract plain text from dict/list/JSON string recursively,
        ưu tiên 'text' hoặc 'content' nếu có, vẫn giữ logic file:/// HTML.
        """
        import os
        import re
        import json

        def html_link_from_path(path):
            import os
            if path.startswith("file://"):
                return path

            if os.path.isabs(path):
                abs_path = path
            else:
                base_dir = "E:/WorkSpace/Agent/Teaching Assistant/Grader/"
                abs_path = os.path.abspath(os.path.join(base_dir, path))

            abs_path = abs_path.replace("\\", "/")
            if not abs_path.startswith("/"):
                abs_path = "/" + abs_path
            return f"file://{abs_path}"

        def extract_all_html_files(obj):
            html_files = set()
            if isinstance(obj, dict):
                for v in obj.values():
                    html_files.update(extract_all_html_files(v))
            elif isinstance(obj, list):
                for item in obj:
                    html_files.update(extract_all_html_files(item))
            elif isinstance(obj, str) and ".html" in obj:
                matches = re.findall(r"([\w\-./\\]+\.html)", obj)
                for m in matches:
                    html_files.add(m.strip())
            return html_files

        def extract_text_recursive(obj):
            if isinstance(obj, dict):
                # Ưu tiên key 'text', sau đó 'content', nếu không thì lặp qua các value
                for key in ["text", "content"]:
                    if key in obj and isinstance(obj[key], str):
                        return obj[key]
                # fallback: check nested dicts
                for v in obj.values():
                    txt = extract_text_recursive(v)
                    if txt:
                        return txt
                return str(obj)

            elif isinstance(obj, list):
                texts = [extract_text_recursive(x) for x in obj if x]
                return " ".join(texts)

            elif isinstance(obj, str):
                try:
                    parsed = json.loads(obj)
                    return extract_text_recursive(parsed)
                except (json.JSONDecodeError, TypeError):
                    return obj

            return str(obj)

        result_text = extract_text_recursive(content)
        html_files = extract_all_html_files(content)
        html_file = max(html_files, key=lambda x: len(x), default=None)
        if html_file:
            return f"{result_text}\n[Link quiz: {html_link_from_path(html_file)}]"
        return result_text

    
    def invoke(self, user_input: str, history: list[dict] = None) -> dict:
        messages = [SystemMessage(content=self._create_system_prompt())]

        history_messages = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history_messages.append(AIMessage(content=msg["content"]))
        
        # Nếu history dài hơn MAX_HISTORY, summarize phần cũ
        if len(history_messages) > self.MAX_HISTORY:
            # Tóm tắt các message cũ
            old_messages = history_messages[:-self.MAX_HISTORY]
            summary_msg = self._summarize_history(old_messages)
            messages.append(summary_msg)
            # Giữ n message cuối
            messages.extend(history_messages[-self.MAX_HISTORY:])
        else:
            messages.extend(history_messages)

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

            if isinstance(last_message, ToolMessage):
                try:
                    data = json.loads(last_message.content)
                    response_content = data.get(
                        "message",
                        "Bạn không có quyền thực hiện yêu cầu này."
                    )
                except Exception:
                    response_content = "Bạn không có quyền thực hiện yêu cầu này."

                return {
                    "response": response_content,
                    "iterations": result["iteration_count"],
                    "tools_used": [],
                    "success": False
                }

            if isinstance(last_message, AIMessage):
                response_content = self._extract_text_from_content(last_message.content)
            else:
                response_content = self._extract_text_from_content(str(last_message))


            # Extract tool calls info
            tool_calls_info = []
            for msg in result["messages"]:
                if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls_info.extend([
                        {"tool": tc["name"], "args": tc.get("args", {})} for tc in msg.tool_calls
                    ])

            return {
                "response": response_content,
                "iterations": result["iteration_count"],
                "tools_used": tool_calls_info,
                "success": True
            }

        except Exception as e:
            return {
                "response": f" Lỗi: {str(e)}",
                "error": str(e),
                "success": False
            }

    
    def stream(self, user_input: str, history: list[dict] = None):
        """Stream agent execution"""
        messages = [SystemMessage(content=self._create_system_prompt())]
        
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


def create_agent(model: str = "llama3.1:latest", max_iterations: int = 10) -> ReActAgent:
    """Factory function để tạo agent"""
    return ReActAgent(model_name=model, max_iterations=max_iterations)


if __name__ == "__main__":
    agent = create_agent()
    
    test_queries = [
        "Xin chào!",
        "Hello, how are you?",
        "Bạn là ai?",
        "What's 2+2?",
        "Tính 123 * 456 + 789",
        "Chấm bài thi cho tôi",
    ]
    
    print(" Testing Fixed ReAct Agent v2\n")
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f" User: {query}")
        print(f"{'='*60}")
        
        result = agent.invoke(query)
        
        print(f"\n Agent: {result['response']}")
        print(f"\n Metadata:")
        print(f"  - Iterations: {result.get('iterations', 0)}")
        print(f"  - Tools used: {result.get('tools_used', [])}")
        print(f"  - Success: {result.get('success', False)}")