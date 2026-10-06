"""Compiled Knowledge Base Service (Karpathy LLM Wiki Pattern).

Thay vì chạy RAG mò mẫm hay truy vấn đồng thời 4 bảng SQL, hệ thống đọc trực tiếp
các trang Markdown chuẩn hóa đã được tiền biên dịch và phê duyệt chuyên môn:
- Cơ sở y tế: data/compiled_wiki/facilities/*.md
- Chuyên khoa y tế: data/compiled_wiki/specialties/*.md
"""

from __future__ import annotations

import logging
from pathlib import Path
import unicodedata
import re

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPILED_WIKI_DIR = PROJECT_ROOT / "data" / "compiled_wiki"


def _normalize_key(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", "_", text).strip()
    return text


class CompiledWikiService:
    _instance: CompiledWikiService | None = None

    def __init__(self, wiki_dir: Path | None = None):
        self.wiki_dir = wiki_dir or COMPILED_WIKI_DIR
        self._facilities_cache: dict[str, str] = {}
        self._specialties_cache: dict[str, str] = {}
        self.reload()

    @classmethod
    def get_instance(cls) -> CompiledWikiService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self) -> None:
        """Nạp toàn bộ compiled wiki vào RAM để phục vụ tức thì."""
        fac_dir = self.wiki_dir / "facilities"
        spec_dir = self.wiki_dir / "specialties"

        self._facilities_cache.clear()
        if fac_dir.exists():
            for f in fac_dir.glob("*.md"):
                try:
                    self._facilities_cache[f.stem.lower()] = f.read_text(encoding="utf-8")
                except Exception as exc:
                    logger.error("Error loading wiki facility %s: %s", f, exc)

        self._specialties_cache.clear()
        if spec_dir.exists():
            for f in spec_dir.glob("*.md"):
                try:
                    self._specialties_cache[f.stem.lower()] = f.read_text(encoding="utf-8")
                except Exception as exc:
                    logger.error("Error loading wiki specialty %s: %s", f, exc)

        logger.info(
            "CompiledWikiService loaded: %d facilities, %d specialties.",
            len(self._facilities_cache),
            len(self._specialties_cache),
        )

    def get_facility_summary(self, facility_query: str) -> str | None:
        """Truy xuất trang wiki cơ sở y tế theo tên hoặc từ khóa."""
        norm_q = _normalize_key(facility_query)
        for key, content in self._facilities_cache.items():
            if key in norm_q or norm_q in key:
                return content
        if "times" in norm_q or "city" in norm_q:
            return self._facilities_cache.get("vinmec_times_city")
        return None

    def get_specialty_summary(self, specialty_name: str) -> str | None:
        """Truy xuất trang wiki chuyên khoa y tế."""
        norm_q = _normalize_key(specialty_name)
        if any(k in norm_q for k in ["than_kinh", "dau_dau", "neurology"]):
            return self._specialties_cache.get("than_kinh")
        if any(k in norm_q for k in ["xuong_khop", "chan_thuong", "orthopedics"]):
            return self._specialties_cache.get("co_xuong_khop")
        for key, content in self._specialties_cache.items():
            if key in norm_q or norm_q in key:
                return content
        return None


def get_compiled_wiki_service() -> CompiledWikiService:
    return CompiledWikiService.get_instance()
