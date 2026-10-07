#!/usr/bin/env python3
"""
scripts/check_docs.py

Script kiểm tra tính nhất quán và các lỗi cấm trong tài liệu (docs/ và context_agent/).
Ngăn chặn các lỗi tái diễn:
  - Khẳng định giữ slot 15 phút / khóa slot 15 phút (mâu thuẫn với HITL)
  - Mã giữ chỗ giả định BK-XXXXXX
  - Đếm sai số lượng kỹ năng ("12 kỹ năng" thay vì 13 kỹ năng)
  - Sử dụng tên công cụ cũ đã bị loại bỏ (search_clinical_specialties)
  - Hardcoded local paths (truong-doing/, file:///d:/...)
"""

import sys
import os
import re
from pathlib import Path

# Thư mục cần quét
DOCS_DIRS = ["context_agent", "docs", "configs"]

# Các file được phép bỏ qua (biên bản lịch sử trước ngày 30/09, file plan/đánh giá phân tích lỗi)
EXCLUDED_FILES = {
    "plan.md",
    "plan2.md",
    "danh_gia_plan2.md",
    "IMPLEMENTATION_UPDATE_2026-09-29.md",
}

# Các quy tắc kiểm tra (tên quy tắc, regex pattern, giải thích lỗi)
BANNED_RULES = [
    (
        "BANNED_15_MIN_SLOT_HOLD",
        re.compile(r"(?:giữ chỗ|khóa slot|tạm giữ.*?slot|hold.*?slot).*?15\s*phút|15-min.*?hold|hold\s+15\s+phút", re.IGNORECASE),
        "Mô tả giữ slot 15 phút đã bị loại bỏ. Hệ thống hiện tại tiếp nhận đặt khám qua HITL (PENDING_CONTACT)."
    ),
    (
        "BANNED_OLD_BOOKING_CODE_BK",
        re.compile(r"BK-[A-Z0-9]{4,}", re.IGNORECASE),
        "Mã giữ chỗ cũ 'BK-XXXXXX' không được dùng cho phản hồi tự động của bot. Dùng mã tiếp nhận 'REQ-XXXXXX' hoặc 'YC-XXXXXX'."
    ),
    (
        "BANNED_OLD_SKILL_COUNT",
        re.compile(r"12\s+kỹ\s+năng", re.IGNORECASE),
        "SKILLS.md hiện tại có 13 kỹ năng (đã bổ sung Kỹ năng 13: LLM Multi-provider Failover)."
    ),
    (
        "BANNED_OBSOLETE_TOOL_NAME",
        re.compile(r"search_clinical_specialties", re.IGNORECASE),
        "Công cụ 'search_clinical_specialties' không còn tồn tại. Sử dụng 'search_doctors' hoặc 'get_department_info'."
    ),
    (
        "BANNED_TRUONG_DOING_PATH",
        re.compile(r"truong-doing[/\\]?", re.IGNORECASE),
        "Đường dẫn cục bộ 'truong-doing' không tồn tại trong repository hiện tại."
    ),
    (
        "BANNED_HARDCODED_FILE_URL",
        re.compile(r"file:///[a-zA-Z]:", re.IGNORECASE),
        "Không dùng đường dẫn tuyệt đối 'file:///C:/...' hoặc 'file:///d:/...'. Dùng relative markdown link."
    ),
]


def check_docs() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    workspace_root = Path(__file__).resolve().parent.parent
    violations = []

    for d in DOCS_DIRS:
        target_dir = workspace_root / d
        if not target_dir.exists():
            continue

        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.endswith(".md"):
                    continue
                if file in EXCLUDED_FILES:
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(workspace_root)

                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception as e:
                    violations.append((str(rel_path), 1, "FILE_READ_ERROR", f"Không đọc được file: {e}"))
                    continue

                lines = text.splitlines()
                for line_num, line in enumerate(lines, start=1):
                    # Bỏ qua các dòng trong chapter-07 / free-accounts nói về Render hosting sleep sau 15 phút
                    if "Render" in line and "sleep" in line:
                        continue
                    if "Cold start" in line and "sleep sau 15 phút" in line:
                        continue

                    for rule_id, pattern, desc in BANNED_RULES:
                        match = pattern.search(line)
                        if match:
                            violations.append(
                                (
                                    str(rel_path),
                                    line_num,
                                    rule_id,
                                    f"[{match.group(0)}] - {desc} (Dòng: '{line.strip()[:100]}...')",
                                )
                            )

    if violations:
        print(f"[FAIL] PHAT HIEN {len(violations)} VI PHAM TRONG TAI LIEU:")
        for file_path, line_num, rule_id, msg in violations:
            print(f"  * {file_path}:{line_num} [{rule_id}]")
            print(f"    -> {msg}")
        return 1

    print("[OK] KIEM TRA TAI LIEU THANH CONG: Toan bo tai lieu nhat quan, khong co chuoi cam.")
    return 0


if __name__ == "__main__":
    sys.exit(check_docs())
