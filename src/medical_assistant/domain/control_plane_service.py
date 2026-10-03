"""Control Plane Service: Nạp và kiểm soát phiên bản Identity Files (Markdown as Control Plane)."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTROL_PLANE_DIR = PROJECT_ROOT / "configs" / "control_plane"


class ControlPlaneService:
    _instance: ControlPlaneService | None = None

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or CONTROL_PLANE_DIR
        self._cache: dict[str, str] = {}
        self._checksums: dict[str, str] = {}
        self.reload()

    @classmethod
    def get_instance(cls) -> ControlPlaneService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self) -> dict[str, str]:
        """Đọc và tính toán checksum cho toàn bộ các file cấu hình Control Plane."""
        new_cache = {}
        new_checksums = {}
        for md_file in self.config_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                key = md_file.stem
                sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
                new_cache[key] = content
                new_checksums[key] = sha
            except Exception as exc:
                logger.error("Failed to load control plane file %s: %s", md_file, exc)
        self._cache = new_cache
        self._checksums = new_checksums
        logger.info("Loaded %d Control Plane identity files: %s", len(self._cache), list(self._cache.keys()))
        return self._checksums

    def get_clinical_soul(self) -> str:
        return self._cache.get("CLINICAL_SOUL", "")

    def get_protocols(self) -> str:
        return self._cache.get("PROTOCOLS", "")

    def get_agent_specs(self) -> str:
        return self._cache.get("AGENTS", "")

    def get_full_control_plane_prompt(self) -> str:
        """Tổng hợp toàn bộ control plane thành context prompt ngắn gọn."""
        parts = []
        if soul := self.get_clinical_soul():
            parts.append(f"=== CLINICAL SOUL & PERSONA ===\n{soul}")
        if protocols := self.get_protocols():
            parts.append(f"=== SAFETY PROTOCOLS & BOUNDARIES ===\n{protocols}")
        return "\n\n".join(parts)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "loaded_files": list(self._cache.keys()),
            "checksums": self._checksums,
        }


def get_control_plane_service() -> ControlPlaneService:
    return ControlPlaneService.get_instance()
