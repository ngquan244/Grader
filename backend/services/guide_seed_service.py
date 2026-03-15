"""
Guide Seed Service
==================
Parses data/user_guide.md and provides:
  1. seed_guides_if_empty(db) — auto-seed the guide_documents table on startup
  2. get_fallback_guide(panel_key) — runtime fallback for missing DB entries
  3. get_all_default_guides()       — list all parsed sections (for list endpoint)
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.guide_document import GuideDocument

logger = logging.getLogger(__name__)

GUIDE_FILE = Path("data/user_guide.md")

# Section title (lowercase) → (panel_key, icon_name, description, sort_order)
SECTION_MAP: dict[str, tuple[str, str, str, int]] = {
    "chat ai":              ("chat",         "MessageSquare", "Giao tiếp AI bằng ngôn ngữ tự nhiên",       1),
    "rag tài liệu":        ("document_rag", "BookText",      "Hỏi đáp thông minh từ tài liệu",            4),
    "canvas lms":           ("canvas",       "GraduationCap", "Tích hợp hệ thống Canvas",                  5),
    "tạo canvas quiz":      ("canvas_quiz",  "PenSquare",     "Tạo & đẩy quiz lên Canvas",                 6),
    "cài đặt":              ("settings",     "Settings",      "Cấu hình model AI & Canvas",                7),
    "câu hỏi thường gặp":  ("faq",          "HelpCircle",    "Giải đáp thắc mắc phổ biến",                8),
}


@dataclass
class DefaultGuide:
    """A guide entry parsed from the markdown file."""
    panel_key: str
    title: str
    description: str
    icon_name: str
    content: str
    sort_order: int


# ── Markdown parser ──────────────────────────────────────────────────

def _parse_user_guide() -> list[DefaultGuide]:
    """Parse data/user_guide.md and return a list of DefaultGuide entries."""
    if not GUIDE_FILE.exists():
        logger.warning("Guide file not found: %s", GUIDE_FILE)
        return []

    raw = GUIDE_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^(?=## )", raw, flags=re.MULTILINE)

    guides: list[DefaultGuide] = []

    # Intro / overview (everything before first ## )
    for part in parts:
        if not part.startswith("## "):
            intro = part.strip()
            if intro:
                guides.append(DefaultGuide(
                    panel_key="overview",
                    title="Tổng quan",
                    description="Giới thiệu hệ thống TA Grader",
                    icon_name="BookOpen",
                    content=intro,
                    sort_order=0,
                ))
            break

    # Per-section
    for part in parts:
        if not part.startswith("## "):
            continue
        heading_match = re.match(r"^## (.+)$", part, re.MULTILINE)
        if not heading_match:
            continue

        title = heading_match.group(1).strip()
        info = SECTION_MAP.get(title.lower())
        if not info:
            continue

        panel_key, icon_name, description, sort_order = info
        body = re.sub(r"^## .+\n?", "", part).strip()

        guides.append(DefaultGuide(
            panel_key=panel_key,
            title=title,
            description=description,
            icon_name=icon_name,
            content=body,
            sort_order=sort_order,
        ))

    return guides


# Cache so we don't re-parse on every request
_cached_defaults: list[DefaultGuide] | None = None


def get_all_default_guides() -> list[DefaultGuide]:
    """Return all default guide entries parsed from user_guide.md (cached)."""
    global _cached_defaults
    if _cached_defaults is None:
        _cached_defaults = _parse_user_guide()
    return _cached_defaults


def get_fallback_guide(panel_key: str) -> Optional[DefaultGuide]:
    """Return the default guide for a specific panel_key, or None."""
    for g in get_all_default_guides():
        if g.panel_key == panel_key:
            return g
    return None


# ── DB seeding ───────────────────────────────────────────────────────

async def seed_guides_if_empty(db: AsyncSession) -> None:
    """Insert default guides into DB if the table is empty."""
    count_result = await db.execute(select(func.count()).select_from(GuideDocument))
    count = count_result.scalar() or 0

    if count > 0:
        logger.info("Guide table already has %d entries — skipping seed.", count)
        return

    defaults = get_all_default_guides()
    if not defaults:
        logger.warning("No default guides parsed from %s — nothing to seed.", GUIDE_FILE)
        return

    for g in defaults:
        db.add(GuideDocument(
            panel_key=g.panel_key,
            title=g.title,
            description=g.description,
            icon_name=g.icon_name,
            content=g.content,
            sort_order=g.sort_order,
            is_published=True,
        ))

    await db.commit()
    logger.info("Seeded %d default guide documents into DB.", len(defaults))
