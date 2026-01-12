"""
ReAct Agent implementation using LangGraph
With Router/Gating to prevent unnecessary tool calls
"""
import json
import re
from typing import TypedDict, Annotated, Sequence, Literal, Optional
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
    route: str  # "no_tools", "allow_tools", "fallback_no_tools"
    tool_error: Optional[str]  # Store tool error for fallback


class ReActAgent:
    """
    ReAct Agent implementation using LangGraph
    With Router/Gating to prevent unnecessary tool calls
    """
    
    # Marker to identify base system prompt (prevents duplicate injection)
    BASE_PROMPT_MARKER = "##BASE_SYSTEM_PROMPT##"
    
    # Gating patterns - compiled once for performance
    GREETING_PATTERNS = re.compile(
        r'^(h[ie]|hello|hey|yo|chào|xin\s*chào|hi+|hê+lo+|hế+lo+|ê+|ơi|alo|a\s*lô)[\s!?.]*$',
        re.IGNORECASE
    )
    
    COMPLIMENT_PATTERNS = re.compile(
        r'(đỉnh|hay|tuyệt|pro|giỏi|ngon|được đó|cảm ơn|thanks|thank you|tks|good|great|nice|awesome|cool|👍|🔥|😄|😊|❤️|💯|🎉|ok|oke|okie|okê|ô kê)',
        re.IGNORECASE
    )
    
    CASUAL_CHAT_PATTERNS = re.compile(
        r'^(ừ|ờ|uhm|hmm|à|ồ|ơ|vâng|dạ|ok|oke|đúng|phải|rồi|yeah|yep|yes|no|không|nope|bye|tạm biệt|goodbye|see you)[\s!?.]*$',
        re.IGNORECASE
    )
    
    # Meta questions about the model itself - deterministic response
    META_MODEL_PATTERNS = re.compile(
        r'(bạn\s*(là|dùng|sử\s*dụng)\s*(mô\s*hình|model|llm|ai)\s*(gì|nào)|model\s*(gì|nào)|mô\s*hình\s*(gì|nào)|you\s*use\s*what\s*model|what\s*model\s*are\s*you)',
        re.IGNORECASE
    )
    
    # Tool trigger patterns - must be explicit
    GRADE_EXAM_PATTERNS = re.compile(
        r'(chấm\s*(bài|điểm|thi)|grade\s*exam|check\s*(answers?|đáp\s*án)|kiểm\s*tra\s*đáp\s*án|chấm\s*đề)',
        re.IGNORECASE
    )
    
    QUIZ_GEN_PATTERNS = re.compile(
        r'(tạo\s*quiz|create\s*quiz|generate\s*quiz|làm\s*quiz|sinh\s*quiz|tạo\s*đề|tạo\s*bài\s*kiểm\s*tra)',
        re.IGNORECASE
    )
    
    CALCULATOR_PATTERNS = re.compile(
        r'(\d+\s*[\+\-\*\/\%\^]\s*\d+|tính|calculate|compute)\s*[\d\+\-\*\/\(\)\.\s]+',
        re.IGNORECASE
    )
    
    # Web search: "cập nhật/update" ONLY with news/online context
    WEB_SEARCH_PATTERNS = re.compile(
        r'(tin\s*tức|news|mới\s*nhất|latest|hôm\s*nay|today|tuần\s*này|this\s*week|search\s*online|tìm\s*trên\s*mạng|(cập\s*nhật|update).*(tin|news|mới|online|mạng)|(tin|news|mới|online|mạng).*(cập\s*nhật|update))',
        re.IGNORECASE
    )
    
    # Report/summary patterns - for grading results aggregation
    REPORT_PATTERNS = re.compile(
        r'(tổng\s*hợp|thống\s*kê|báo\s*cáo|summary|report|aggregate).*(kết\s*quả|điểm|mã\s*đề|results?|scores?)|((kết\s*quả|điểm|mã\s*đề|results?|scores?).*(tổng\s*hợp|thống\s*kê|báo\s*cáo|summary|report))',
        re.IGNORECASE
    )
    
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
        
        # Initialize LLM - TWO SEPARATE PATHS
        # Path 1: Plain LLM without tools (for greetings, general knowledge, fallback)
        self.llm_plain = ChatOllama(
            model=model_name,
            temperature=temperature,
        )
        
        # Path 2: LLM with tools bound (only for explicit tool requests)
        self.llm = ChatOllama(
            model=model_name,
            temperature=temperature,
        )
        
        # Get tools
        self.tools = get_all_tools()
        
        # Bind tools to LLM - ONLY used in allow_tools path
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _classify_input(self, user_input: str) -> str:
        """
        Rule-based router to classify user input.
        Returns: "no_tools", "allow_tools", "default_no_tools", or "meta_model"
        """
        text = user_input.strip()
        text_lower = text.lower()
        
        # 0. Meta questions about the model - deterministic response
        if self.META_MODEL_PATTERNS.search(text):
            return "meta_model"
        
        # 1. Very short messages (<=15 chars or <=4 words) - likely casual chat
        word_count = len(text.split())
        char_count = len(text)
        
        # Check for greetings first (high priority no-tool)
        if self.GREETING_PATTERNS.match(text):
            return "no_tools"
        
        # Check for casual chat patterns
        if self.CASUAL_CHAT_PATTERNS.match(text):
            return "no_tools"
        
        # Check for compliments (can be anywhere in text)
        if self.COMPLIMENT_PATTERNS.search(text) and word_count <= 6:
            return "no_tools"
        
        # Short messages without explicit tool triggers -> no tools
        if char_count <= 15 or word_count <= 3:
            # Unless it's a clear calculation
            if self.CALCULATOR_PATTERNS.search(text):
                return "allow_tools"
            return "no_tools"
        
        # Just mentioning "tool" or "tools" is NOT enough to trigger tools
        if re.match(r'^.*\btool[s]?\b.*$', text_lower) and word_count <= 5:
            # User just mentions "tool" without clear intent
            return "default_no_tools"
        
        # 2. Check for EXPLICIT tool triggers
        if self.GRADE_EXAM_PATTERNS.search(text):
            return "allow_tools"
        
        if self.QUIZ_GEN_PATTERNS.search(text):
            return "allow_tools"
        
        if self.CALCULATOR_PATTERNS.search(text):
            return "allow_tools"
        
        if self.WEB_SEARCH_PATTERNS.search(text):
            return "allow_tools"
        
        # Report/summary patterns - may need tool if data exists
        if self.REPORT_PATTERNS.search(text):
            return "allow_tools"
        
        # 3. Default: answer with plain LLM (no tools)
        # This covers general knowledge questions
        return "default_no_tools"
    
    def _create_system_prompt(self, allow_tools: bool = False) -> str:
        """
        System prompt - varies based on whether tools are allowed.
        Includes BASE_PROMPT_MARKER for identification.
        """
        base_prompt = f"""{self.BASE_PROMPT_MARKER}
You are a helpful AI assistant. Answer user questions naturally and accurately.

Important:
- Always answer greetings, casual chat, compliments naturally and warmly.
- Always answer general knowledge questions directly from your knowledge.
- Only apologize if you truly cannot answer or the data is missing.
- Do not make up numbers or facts. If unsure, say "I don't know".
- For subjective questions, clarify it is opinion-based.
- NEVER say "I don't have permission" or "I cannot access" for general questions.
- If asked about data/results that you don't have, ask the user to provide the data or specify the file/source.
"""
        
        if allow_tools:
            tool_descriptions = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in self.tools
            ])
            
            return base_prompt + f"""
You have access to the following tools:
{tool_descriptions}

Tool usage rules:
- execute_notebook → ONLY when user explicitly asks to "grade exam", "check answers", "chấm bài", "chấm điểm"
- quiz_generator → ONLY when user explicitly asks to "create quiz", "tạo quiz", "tạo đề"
- calculator → ONLY for explicit numeric calculations (e.g., 123 * 456 + 789)
- web_search → ONLY for current events, news, or up-to-date information

When using tools:
- Extract and display full information from results
- Format output clearly
- If a tool returns an error, explain the issue and answer from your knowledge if possible
"""
        else:
            return base_prompt + """
Answer the user's question directly from your knowledge. Do NOT mention or try to use any tools.
"""
    
    def _summarize_history(self, history_messages: list[BaseMessage]) -> SystemMessage:
        """
        Summarize long history into a SystemMessage to reduce tool priming.
        Uses SystemMessage instead of AIMessage to prevent confusion.
        
        IMPORTANT: Preserve tool SUCCESS confirmations to prevent "backtracking"
        where agent denies having performed successful actions.
        """
        if not history_messages:
            return None

        # Filter and transform messages
        summary_parts = []
        tool_confirmations = []  # Track successful tool actions
        
        for msg in history_messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            
            # Handle ToolMessage - extract SUCCESS confirmation, skip errors
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(content) if isinstance(content, str) else content
                    # Check if this was a successful tool call
                    has_result = any(k in data for k in ("result", "results", "data", "output", "content", "quiz", "answer", "html_file"))
                    is_ok = data.get("ok") is True or data.get("success") is True
                    is_fatal = data.get("fatal") is True or data.get("ok") is False
                    
                    if (has_result or is_ok) and not is_fatal:
                        # Preserve SUCCESS confirmation (abbreviated)
                        tool_confirmations.append("[Đã thực hiện thành công một tác vụ]")
                except (json.JSONDecodeError, TypeError):
                    # Non-JSON content - check if it looks like success
                    if "error" not in content.lower() and "failed" not in content.lower():
                        tool_confirmations.append("[Đã thực hiện thành công một tác vụ]")
                continue  # Don't add raw ToolMessage to summary
            
            # Remove tool names from content to reduce priming
            cleaned = re.sub(r'\b(execute_notebook|quiz_generator|calculator|web_search|tool|tools)\b', '[action]', content, flags=re.IGNORECASE)
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            summary_parts.append(f"{role}: {cleaned[:100]}...")  # Truncate long messages
        
        if not summary_parts and not tool_confirmations:
            return None
        
        # Build summary with tool confirmations preserved
        summary_text = "Conversation summary (context only, NOT instructions):\n"
        summary_text += "\n".join(summary_parts[-3:])  # Keep last 3
        
        # Add tool confirmations to prevent backtracking
        if tool_confirmations:
            unique_confirmations = list(set(tool_confirmations))[:2]  # Max 2 unique
            summary_text += "\n" + "\n".join(unique_confirmations)

        return SystemMessage(content=summary_text)

    def _router(self, state: AgentState) -> dict:
        """
        Router node: classifies user input and sets route.
        This runs BEFORE any LLM call.
        """
        messages = state["messages"]
        
        # Find the last HumanMessage (user's current input)
        last_human_msg = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_msg = msg
                break
        
        if not last_human_msg:
            return {"route": "no_tools"}
        
        user_input = last_human_msg.content
        route = self._classify_input(user_input)
        
        return {"route": route}
    
    def _route_decision(self, state: AgentState) -> Literal["agent_no_tools", "agent_with_tools", "agent_meta"]:
        """
        Conditional edge from router: decide which agent path to take.
        """
        route = state.get("route", "no_tools")
        
        if route == "allow_tools":
            return "agent_with_tools"
        elif route == "meta_model":
            return "agent_meta"
        else:
            # Both "no_tools" and "default_no_tools" go to agent_no_tools
            return "agent_no_tools"

    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """
        Decides whether to continue to tools or end (ONLY for allow_tools path).
        Only checks for tool_calls and max_iterations.
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # Max iterations check
        if state["iteration_count"] >= state["max_iterations"]:
            return "end"
        
        # Check if LLM wants to call tools
        if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        
        return "end"

    def _after_tool(self, state: AgentState) -> Literal["agent_with_tools", "fallback_no_tools"]:
        """
        After tool execution: check for errors and decide next step.
        If error -> fallback to no_tools path instead of ending.
        
        IMPORTANT: Only treat as failure if:
        1. fatal=True explicitly
        2. ok=False explicitly  
        3. No result/data AND has error message
        
        DO NOT treat warnings or non-empty error strings as failures if there's valid result.
        """
        last_msg = state["messages"][-1]

        if isinstance(last_msg, ToolMessage):
            try:
                data = json.loads(last_msg.content)
                
                # Case 1: Explicit fatal error
                if data.get("fatal") is True:
                    return "fallback_no_tools"
                
                # Case 2: Explicit ok=False (strict check)
                if data.get("ok") is False:
                    return "fallback_no_tools"
                
                # Case 3: Has result/data -> SUCCESS even with warnings
                has_result = any(k in data for k in ("result", "results", "data", "output", "content", "quiz", "answer", "html_file"))
                if has_result:
                    return "agent_with_tools"  # SUCCESS
                
                # Case 4: Explicit ok=True or success=True -> SUCCESS
                if data.get("ok") is True or data.get("success") is True:
                    return "agent_with_tools"  # SUCCESS
                
                # Case 5: No result AND has error -> FAILURE
                if data.get("error") and not has_result:
                    return "fallback_no_tools"
                    
            except (json.JSONDecodeError, TypeError):
                # If content is not JSON, check for CRITICAL error keywords only
                content_lower = str(last_msg.content).lower()
                # Only fail on critical keywords, not warnings
                critical_keywords = ["fatal error", "exception:", "traceback", "crashed", "aborted"]
                if any(kw in content_lower for kw in critical_keywords):
                    return "fallback_no_tools"

        # Default: SUCCESS - continue with tools if needed
        return "agent_with_tools"
    
    def _has_base_system_prompt(self, messages: list) -> bool:
        """
        Check if base system prompt (with marker) is already present.
        """
        for msg in messages:
            if isinstance(msg, SystemMessage) and self.BASE_PROMPT_MARKER in msg.content:
                return True
        return False
    
    def _call_model_no_tools(self, state: AgentState) -> dict:
        """
        Call LLM WITHOUT tools - for greetings, general knowledge, fallback.
        """
        messages = list(state["messages"])
        
        # Ensure BASE system prompt is present (check marker, not just any SystemMessage)
        if not self._has_base_system_prompt(messages):
            system_msg = SystemMessage(content=self._create_system_prompt(allow_tools=False))
            messages = [system_msg] + messages
        
        # Check if this is a fallback from tool error
        tool_error = state.get("tool_error")
        if tool_error:
            # Add context about the error so LLM can respond helpfully
            messages.append(SystemMessage(content=f"Note: A tool encountered an error. Please answer from your knowledge instead. Error: {tool_error}"))
        
        # Call plain LLM (no tools)
        response = self.llm_plain.invoke(messages)
        
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1
        }
    
    def _call_model_with_tools(self, state: AgentState) -> dict:
        """
        Call LLM WITH tools - only for explicit tool requests.
        """
        messages = list(state["messages"])
        
        # Ensure BASE system prompt is present (check marker, not just any SystemMessage)
        if not self._has_base_system_prompt(messages):
            system_msg = SystemMessage(content=self._create_system_prompt(allow_tools=True))
            messages = [system_msg] + messages
        
        # Call LLM with tools bound
        response = self.llm_with_tools.invoke(messages)
        
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1
        }
    
    def _call_model_meta(self, state: AgentState) -> dict:
        """
        Deterministic response for meta questions about the model.
        Returns model info without calling LLM.
        """
        meta_response = f"Tôi đang sử dụng mô hình {self.model_name} chạy local thông qua Ollama. Đây là một LLM (Large Language Model) được triển khai trên máy của bạn."
        
        return {
            "messages": [AIMessage(content=meta_response)],
            "iteration_count": state["iteration_count"] + 1
        }
    
    def _fallback_handler(self, state: AgentState) -> dict:
        """
        Fallback handler when tool fails - uses plain LLM to respond.
        """
        messages = list(state["messages"])
        
        # Get the last tool error if any
        last_msg = messages[-1] if messages else None
        error_context = ""
        if isinstance(last_msg, ToolMessage):
            try:
                data = json.loads(last_msg.content)
                error_context = data.get("message", data.get("error", str(last_msg.content)))
            except:
                error_context = str(last_msg.content)
        
        # Create a helpful fallback prompt
        fallback_prompt = SystemMessage(content=f"""The requested action could not be completed. 
Please provide a helpful response to the user based on your knowledge.
If the user asked for something specific that failed, explain what might have gone wrong and offer alternatives.
Context: {error_context[:200]}""")
        
        # Find the last human message
        last_human = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human = msg
                break
        
        fallback_messages = [
            SystemMessage(content=self._create_system_prompt(allow_tools=False)),
            fallback_prompt
        ]
        if last_human:
            fallback_messages.append(last_human)
        
        response = self.llm_plain.invoke(fallback_messages)
        
        return {
            "messages": [response],
            "iteration_count": state["iteration_count"] + 1,
            "tool_error": None  # Clear the error
        }
    
    def _build_graph(self) -> StateGraph:
        """
        Build StateGraph with Router/Gating architecture:
        
        entry -> router -> (decision)
            -> agent_no_tools -> END
            -> agent_with_tools -> (should_continue)
                -> tools -> (after_tool)
                    -> agent_with_tools (success)
                    -> fallback_no_tools -> END (error)
                -> END (no tool calls)
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self._router)
        workflow.add_node("agent_no_tools", self._call_model_no_tools)
        workflow.add_node("agent_with_tools", self._call_model_with_tools)
        workflow.add_node("agent_meta", self._call_model_meta)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("fallback_no_tools", self._fallback_handler)
        
        # Set entry point - always go through router first
        workflow.set_entry_point("router")
        
        # Router decides which path to take
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "agent_no_tools": "agent_no_tools",
                "agent_with_tools": "agent_with_tools",
                "agent_meta": "agent_meta"
            }
        )
        
        # agent_no_tools always ends (no tool calls possible)
        workflow.add_edge("agent_no_tools", END)
        
        # agent_meta always ends (deterministic response)
        workflow.add_edge("agent_meta", END)
        
        # agent_with_tools may call tools or end
        workflow.add_conditional_edges(
            "agent_with_tools",
            self._should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        # After tools: success -> back to agent, error -> fallback
        workflow.add_conditional_edges(
            "tools",
            self._after_tool,
            {
                "agent_with_tools": "agent_with_tools",
                "fallback_no_tools": "fallback_no_tools"
            }
        )
        
        # Fallback always ends
        workflow.add_edge("fallback_no_tools", END)

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
        """
        Main entry point for agent invocation.
        Returns: dict with response, iterations, tools_used, success
        """
        messages = []
        
        # Process history - INCLUDING tool messages for evidence persistence
        history_messages = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history_messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "tool":
                    # IMPORTANT: Preserve tool evidence across turns
                    # This prevents agent from "backtracking" on successful tool calls
                    tool_id = msg.get("tool_call_id", "tool_result")
                    history_messages.append(ToolMessage(
                        content=msg["content"],
                        tool_call_id=tool_id
                    ))
        
        # Summarize old history if too long (reduces tool priming)
        if len(history_messages) > self.MAX_HISTORY:
            old_messages = history_messages[:-self.MAX_HISTORY]
            summary_msg = self._summarize_history(old_messages)
            if summary_msg:
                messages.append(summary_msg)
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
            "max_iterations": self.max_iterations,
            "route": "no_tools",  # Default, will be set by router
            "tool_error": None
        }

        # Run graph
        try:
            result = self.graph.invoke(initial_state)

            # Extract response from last message
            last_message = result["messages"][-1]
            
            # Handle different message types
            if isinstance(last_message, ToolMessage):
                # This shouldn't happen with new architecture, but handle it
                try:
                    data = json.loads(last_message.content)
                    if data.get("error") or data.get("fatal"):
                        # Tool failed but we should have gone to fallback
                        # Return a helpful message instead of "no permission"
                        response_content = "Xin lỗi, tôi không thể thực hiện yêu cầu này. Bạn có thể cho tôi biết thêm chi tiết?"
                    else:
                        response_content = self._extract_text_from_content(data)
                except (json.JSONDecodeError, TypeError):
                    response_content = self._extract_text_from_content(last_message.content)
                    
                return {
                    "response": response_content,
                    "iterations": result.get("iteration_count", 1),
                    "tools_used": [],
                    "success": True  # Changed from False - we handled it
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
                "iterations": result.get("iteration_count", 1),
                "tools_used": tool_calls_info,
                "success": True
            }

        except Exception as e:
            return {
                "response": f"Đã xảy ra lỗi: {str(e)}",
                "error": str(e),
                "iterations": 0,
                "tools_used": [],
                "success": False
            }

    
    def stream(self, user_input: str, history: list[dict] = None):
        """Stream agent execution - uses same logic as invoke() for consistency"""
        messages = []
        
        # Process history - INCLUDING tool messages for evidence persistence (same as invoke)
        history_messages = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history_messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "tool":
                    # IMPORTANT: Preserve tool evidence across turns (same as invoke)
                    tool_id = msg.get("tool_call_id", "tool_result")
                    history_messages.append(ToolMessage(
                        content=msg["content"],
                        tool_call_id=tool_id
                    ))
        
        # Summarize old history if too long (same as invoke)
        if len(history_messages) > self.MAX_HISTORY:
            old_messages = history_messages[:-self.MAX_HISTORY]
            summary_msg = self._summarize_history(old_messages)
            if summary_msg:
                messages.append(summary_msg)
            messages.extend(history_messages[-self.MAX_HISTORY:])
        else:
            messages.extend(history_messages)
        
        # Add current user input
        messages.append(HumanMessage(content=user_input))
        
        # Create initial state (same structure as invoke - let nodes handle system prompt)
        initial_state = {
            "messages": messages,
            "next_action": "continue",
            "iteration_count": 0,
            "max_iterations": self.max_iterations,
            "route": "no_tools",  # Default, will be set by router
            "tool_error": None
        }
        
        # Stream execution
        for output in self.graph.stream(initial_state):
            yield output


def create_agent(model: str = "llama3.1:latest", max_iterations: int = 10) -> ReActAgent:
    """Factory function để tạo agent"""
    return ReActAgent(model_name=model, max_iterations=max_iterations)
