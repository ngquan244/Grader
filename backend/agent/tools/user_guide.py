"""
User Guide Tool
Provides application usage guidance.
Priority: DB guide_documents (admin-editable) → data/user_guide.md (fallback).
The agent uses this tool to help users and always includes a link to /guide.
"""

import asyncio
import json
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .base import logger

__all__ = ["UserGuideTool", "UserGuideInput"]

GUIDE_FILE = "data/user_guide.md"

# Map guide section titles (lowercase) → panel config key
SECTION_PANEL_MAP = {
    "chat ai": "chat",
    "rag tài liệu": "document_rag",
    "canvas lms": "canvas",
    "tạo canvas quiz": "canvas_quiz",
    "cài đặt": "settings",
}

# FAQ question keywords → required panel keys
FAQ_PANEL_MAP = [
    {"keywords": ["tài liệu đã upload", "nội dung tài liệu"], "panels": ["document_rag"]},
    {"keywords": ["tính năng bị khóa"], "panels": ["chat"]},
    {"keywords": ["ollama", "groq"], "panels": ["settings"]},
    {"keywords": ["quiz từ tài liệu", "đẩy lên canvas"], "panels": ["document_rag", "canvas_quiz"]},
]


def _get_hidden_panels() -> set:
    """Return set of panel keys that are currently disabled."""
    try:
        from backend.services.panel_config_service import get_panel_config
        config = get_panel_config()
        return {k for k, v in config.items() if not v}
    except Exception:
        return set()


def _read_guide_from_db() -> str | None:
    """Try reading guide content from DB (guide_documents table).
    Returns combined markdown string or None on failure."""
    try:
        from backend.database.base import AsyncSessionLocal
        from backend.services.guide_service import list_guides

        async def _fetch():
            async with AsyncSessionLocal() as db:
                guides = await list_guides(db, include_unpublished=False)
                if not guides:
                    return None
                parts = []
                for g in sorted(guides, key=lambda x: x.sort_order):
                    if g.panel_key == "overview":
                        parts.insert(0, g.content)
                    else:
                        parts.append(f"## {g.title}\n\n{g.content}")
                return "\n\n---\n\n".join(parts) if parts else None

        # Run in new event loop on a separate thread to avoid conflicts
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(lambda: asyncio.run(_fetch())).result(timeout=5)
            return result
        else:
            return asyncio.run(_fetch())
    except Exception as e:
        logger.debug("Could not read guides from DB (falling back to file): %s", e)
        return None


def _read_guide() -> str:
    """Read guide content: DB first, then markdown file fallback.
    Filters out sections for hidden panels."""
    # Try DB first
    db_content = _read_guide_from_db()
    if db_content and db_content.strip():
        return db_content

    # Fallback: read markdown file
    from pathlib import Path
    import re

    path = Path(GUIDE_FILE)
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8")

    hidden = _get_hidden_panels()
    if not hidden:
        return raw

    # Split on ## headings while keeping each section together
    parts = re.split(r'^(?=## )', raw, flags=re.MULTILINE)

    filtered = []
    for part in parts:
        if not part.startswith("## "):
            # Intro section — keep but strip hidden feature names from summary
            for panel_key in hidden:
                # Remove bold feature names matching hidden panels
                feature_names = {
                    "chat": "Chat AI",
                    "document_rag": "RAG Tài Liệu",
                    "canvas": "Canvas LMS",
                    "canvas_quiz": "Tạo Canvas Quiz",
                }
                name = feature_names.get(panel_key)
                if name:
                    escaped = re.escape(name)
                    part = re.sub(rf',?\s*\*\*{escaped}\*\*,?', lambda m: ',' if m.group().startswith(',') and m.group().endswith(',') else '', part)
            # Clean up leftover commas
            part = re.sub(r',\s*,', ',', part)
            part = re.sub(r':\s*,\s*', ': ', part)
            part = re.sub(r',\s*\.', '.', part)
            filtered.append(part)
            continue

        # Extract heading title
        heading_match = re.match(r'^## (.+)$', part, re.MULTILINE)
        if not heading_match:
            filtered.append(part)
            continue

        title = heading_match.group(1).strip().lower()
        panel_key = SECTION_PANEL_MAP.get(title)

        if panel_key and panel_key in hidden:
            continue  # skip this section

        filtered.append(part)

    result = "".join(filtered)

    # Filter FAQ ### sub-questions inside ## Câu hỏi thường gặp
    def _filter_faq(m: re.Match) -> str:
        faq_block = m.group(0)
        faq_parts = re.split(r'^(?=### )', faq_block, flags=re.MULTILINE)
        kept = []
        for faq in faq_parts:
            if not faq.startswith("### "):
                kept.append(faq)
                continue
            faq_heading = re.match(r'^### (.+)$', faq, re.MULTILINE)
            faq_title = faq_heading.group(1).lower() if faq_heading else ""
            should_hide = False
            for rule in FAQ_PANEL_MAP:
                if any(kw in faq_title for kw in rule["keywords"]):
                    if any(p in hidden for p in rule["panels"]):
                        should_hide = True
                    break
            if not should_hide:
                kept.append(faq)
        return "".join(kept)

    result = re.sub(r'## Câu hỏi thường gặp[\s\S]*?(?=\n## |$)', _filter_faq, result)

    return result


class UserGuideInput(BaseModel):
    """Input schema for user guide tool"""
    topic: str = Field(
        description="Chủ đề hoặc câu hỏi mà người dùng cần hướng dẫn (ví dụ: 'cách upload tài liệu', 'cách chấm bài')"
    )


class UserGuideTool(BaseTool):
    """
    Tool hướng dẫn người dùng sử dụng ứng dụng.

    Reads from an admin-editable guide document (data/user_guide.md) and answers
    user questions about how to use the application's features.
    Always includes a link to /guide for the user to view the full guide.
    """

    name: str = "user_guide"
    description: str = """
    Hướng dẫn người dùng sử dụng các tính năng của ứng dụng TA Grader.

    Sử dụng khi người dùng hỏi:
    - Cách sử dụng ứng dụng / tính năng
    - Hướng dẫn upload tài liệu, chấm bài, hỏi đáp RAG, v.v.
    - "Làm sao để ...?", "Hướng dẫn ...", "Cách dùng ..."
    - "Help", "Trợ giúp", "Giúp tôi"

    Tool sẽ:
    1. Đọc tài liệu hướng dẫn (do admin biên soạn)
    2. Tìm phần liên quan đến câu hỏi
    3. Trả lời kèm link đến trang /guide để xem hướng dẫn đầy đủ
    """
    args_schema: Type[BaseModel] = UserGuideInput

    def _run(self, topic: str) -> str:
        """
        Look up guidance for the given topic from the admin-editable guide.

        Args:
            topic: The topic or question the user needs help with

        Returns:
            JSON with relevant guidance and a link to /guide
        """
        try:
            logger.info(f"User guide query: {topic}")

            guide_content = _read_guide()

            if not guide_content.strip():
                return json.dumps({
                    "answer": (
                        "Tài liệu hướng dẫn hiện chưa được admin biên soạn. "
                        "Vui lòng liên hệ quản trị viên để cập nhật hướng dẫn.\n\n"
                        "Bạn có thể truy cập trang [Hướng dẫn](/guide) để xem đầy đủ."
                    ),
                    "guide_url": "/guide",
                    "status": "empty_guide"
                }, ensure_ascii=False, indent=2)

            # Find relevant sections by simple keyword matching
            topic_lower = topic.lower()
            sections = guide_content.split("\n## ")
            relevant_parts = []

            # Always include the intro/header
            if sections:
                header = sections[0]
                if header.strip():
                    relevant_parts.append(header.strip())

            # Search for relevant sections
            keywords = topic_lower.split()
            for section in sections[1:]:
                section_lower = section.lower()
                # Check if any keyword appears in section title or content
                if any(kw in section_lower for kw in keywords):
                    relevant_parts.append("## " + section.strip())

            # If no specific section matched, return the full guide
            if len(relevant_parts) <= 1:
                relevant_text = guide_content
            else:
                relevant_text = "\n\n".join(relevant_parts)

            # Truncate if too long (keep first 3000 chars)
            if len(relevant_text) > 3000:
                relevant_text = relevant_text[:3000] + "\n\n... (xem đầy đủ tại [Hướng dẫn](/guide))"

            response = {
                "topic": topic,
                "guide_content": relevant_text,
                "guide_url": "/guide",
                "message": "Xem hướng dẫn đầy đủ tại trang [Hướng dẫn](/guide)",
                "status": "success"
            }

            logger.info(f"Guide query successful for topic: {topic}")
            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error reading user guide: {e}", exc_info=True)
            return json.dumps({
                "error": f"Lỗi khi đọc hướng dẫn: {str(e)}",
                "guide_url": "/guide",
                "status": "error"
            }, ensure_ascii=False, indent=2)

    async def _arun(self, topic: str) -> str:
        """Async version — delegates to sync _run."""
        return self._run(topic)
