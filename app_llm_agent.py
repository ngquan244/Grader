import gradio as gr
import re
import json
import subprocess
from typing import List, Dict, Optional, Tuple
from kaggle_tool import get_score_from_kaggle


def ollama_chat(messages: List[Dict], model: str = "llama3.1:latest", system_prompt: Optional[str] = None) -> str:
    """
    Gọi Ollama CLI với system prompt và structured messages
    """
    formatted_parts = []
    if system_prompt:
        formatted_parts.append(f"System: {system_prompt}")

    for m in messages:
        role = m['role'].capitalize()
        formatted_parts.append(f"{role}: {m['content']}")

    formatted = "\n".join(formatted_parts)

    cmd = ["ollama", "run", model]
    result = subprocess.run(cmd, input=formatted.encode(), capture_output=True)

    if result.returncode != 0:
        raise RuntimeError(f"Ollama error: {result.stderr.decode()}")

    return result.stdout.decode().strip()


# TOOLS REGISTRY
TOOLS = {
    "get_kaggle_score": {
        "description": "Lấy điểm số từ Kaggle competition. Sử dụng khi người dùng muốn kiểm tra kết quả submission.",
        "keywords": ["kaggle", "score", "điểm", "chấm điểm", "submission", "kết quả"],
        "function": lambda: get_score_from_kaggle(run_local_kernel=False)
    }
}


def execute_tool(tool_name: str) -> str:
    """Execute tool và format output"""
    if tool_name not in TOOLS:
        return f" Tool '{tool_name}' không tồn tại"

    try:
        result = TOOLS[tool_name]["function"]()
        return f" **Tool Output ({tool_name}):**\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
    except Exception as e:
        return f" Tool '{tool_name}' gặp lỗi: {type(e).__name__}: {str(e)}"


def get_tools_description() -> str:
    descriptions = []
    for name, info in TOOLS.items():
        descriptions.append(f"- **{name}**: {info['description']}")
    return "\n".join(descriptions)


# ENHANCED AGENT CLASS
class EnhancedAgent:
    def __init__(self, model: str = "llama3.1:latest", max_history: int = 10):
        self.history: List[Dict] = []
        self.model = model
        self.max_history = max_history
        self.system_prompt = self._build_system_prompt()



    def _build_system_prompt(self) -> str:
        tools_desc = get_tools_description()
        return f"""Bạn là trợ lý AI thông minh có khả năng sử dụng tools để giúp người dùng.

**Available Tools:**
{tools_desc}

**Instructions:**
1. Phân tích yêu cầu của người dùng cẩn thận
2. Nếu cần dùng tool, trả lời chính xác: USE_TOOL:<tool_name>
3. Nếu không cần tool, trả lời trực tiếp và hữu ích
4. Luôn lịch sự, rõ ràng và súc tích
5. Nếu không chắc chắn, hỏi làm rõ thay vì đoán

Ví dụ:
- User: "Cho tôi điểm Kaggle" → Response: "USE_TOOL:get_kaggle_score"
- User: "Giải thích machine learning" → Response: <giải thích trực tiếp>
"""

    def reset(self):
        """Reset conversation history"""
        self.history = []

    def _trim_history(self):
        """Giữ history trong giới hạn để tránh context quá dài"""
        if len(self.history) > self.max_history * 2:
            # Giữ lại system message và messages gần nhất
            self.history = self.history[-(self.max_history * 2):]

    def _should_use_tool(self, user_message: str) -> Optional[str]:
        """
        Sử dụng LLM để quyết định có cần tool không
        Returns: tool_name nếu cần, None nếu không
        """
        text_lower = user_message.lower()
        for tool_name, tool_info in TOOLS.items():
            if any(kw in text_lower for kw in tool_info["keywords"]):
                # Có keyword match, hỏi LLM confirm
                break

        # Dùng LLM reasoning
        reasoning_messages = [{
            "role": "user",
            "content": f"""Phân tích yêu cầu: "{user_message}"

Người dùng có muốn sử dụng tool không? Nếu có, tool nào?

Trả lời CHÍNH XÁC theo format:
- Nếu cần tool: USE_TOOL:<tool_name>
- Nếu không: NO_TOOL

Available tools: {', '.join(TOOLS.keys())}"""
        }]

        try:
            response = ollama_chat(reasoning_messages, self.model, self.system_prompt)

            # Parse response
            if "USE_TOOL:" in response:
                tool_name = response.split("USE_TOOL:")[1].strip().split()[0]
                if tool_name in TOOLS:
                    return tool_name

            return None
        except Exception as e:
            print(f" Tool detection error: {e}")
            return None

    def handle_message(self, user_message: str) -> str:
        """
        Xử lý tin nhắn với intelligent tool selection và context awareness
        """
        # Trim history nếu quá dài
        self._trim_history()

        # Check nếu là greeting đơn giản
        if re.search(r'^\s*(hi|hello|chào|hey)\s*[!.?]*\s*$', user_message.lower()):
            return " Xin chào! Tôi là trợ lý AI của bạn. Tôi có thể giúp bạn:\n- Kiểm tra điểm Kaggle\n- Trả lời câu hỏi\n- Và nhiều hơn nữa!\n\nBạn cần gì?"

        # Intelligent tool detection
        tool_name = self._should_use_tool(user_message)

        if tool_name:
            # Execute tool
            tool_output = execute_tool(tool_name)

            # Thêm vào history
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": tool_output})

            # Tạo summary response từ tool output
            summary_prompt = [{
                "role": "user",
                "content": f"""Người dùng hỏi: "{user_message}"

Tool đã trả về kết quả:
{tool_output}

Hãy tóm tắt kết quả này một cách dễ hiểu và hữu ích cho người dùng. Giữ nguyên các con số quan trọng."""
            }]

            try:
                summary = ollama_chat(summary_prompt, self.model)
                return f"{tool_output}\n\n---\n\n **Tóm tắt:** {summary}"
            except:
                return tool_output

        else:
            # Normal conversation - thêm context
            self.history.append({"role": "user", "content": user_message})

            try:
                reply = ollama_chat(self.history, self.model, self.system_prompt)
                self.history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                error_msg = f" Lỗi: {str(e)}"
                self.history.append({"role": "assistant", "content": error_msg})
                return error_msg


# GRADIO UI
def create_ui():
    agent = EnhancedAgent()

    with gr.Blocks(title="Smart LLM Agent", theme=gr.themes.Monochrome()) as demo:
        gr.Markdown("""
        #  Smart LLM Agent với Ollama
        Agent thông minh tích hợp Kaggle tool và khả năng reasoning
        """)

        with gr.Row():
            with gr.Column(scale=2):
                model_selector = gr.Dropdown(
                    ["llama3.1:latest", "phi3:latest", "mistral:latest", "gemma2:latest"],
                    value="llama3.1:latest",
                    label="Chọn Model",
                )
            with gr.Column(scale=1):
                max_history = gr.Slider(
                    minimum=5, maximum=50, value=10, step=5,
                    label=" Max History",
                )
            with gr.Column(scale=1):
                clear_btn = gr.Button("Xóa Chat", variant="secondary")

        chatbox = gr.Chatbot(
            height=500,
            type="messages",
            label="Conversation",
            show_copy_button=True
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Nhập tin nhắn... (VD: 'Cho tôi điểm Kaggle' hoặc 'Giải thích AI là gì?')",
                label="Message",
                scale=9
            )
            submit_btn = gr.Button("Send", variant="primary", scale=1)

        gr.Markdown("""
        **Tips:**
        - Yêu cầu điểm Kaggle: "cho tôi điểm", "kiểm tra score"
        - Hỏi đáp chung: agent sẽ trả lời trực tiếp
        - Agent tự động giữ context của cuộc hội thoại
        """)

        state = gr.State(agent)

        def user_submit(user_message, chat_agent, model, max_hist):
            if not user_message.strip():
                return "", chat_agent.history, chat_agent

            chat_agent.model = model
            chat_agent.max_history = max_hist

            reply = chat_agent.handle_message(user_message)

            display_history = chat_agent.history[-20:]  # Show last 20 messages

            return "", display_history, chat_agent

        def reset_agent():
            new_agent = EnhancedAgent()
            return new_agent, []

        msg.submit(
            user_submit,
            [msg, state, model_selector, max_history],
            [msg, chatbox, state]
        )
        submit_btn.click(
            user_submit,
            [msg, state, model_selector, max_history],
            [msg, chatbox, state]
        )
        clear_btn.click(reset_agent, None, [state, chatbox])

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)