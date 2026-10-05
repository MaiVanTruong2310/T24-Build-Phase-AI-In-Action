"""Helper functions shared across LangGraph agent nodes."""

from __future__ import annotations


def extract_facility_inquiry(query: str) -> tuple[bool, str | None]:
    """Phát hiện linh hoạt ý định hỏi nơi khám / bệnh viện / cơ sở kèm khu vực địa lý."""
    q = query.lower()
    region = None
    if any(k in q for k in ["hà nội", "ha noi", "hn"]):
        region = "Hà Nội"
    elif any(k in q for k in ["hồ chí minh", "tp hcm", "tphcm", "sài gòn", "sai gon", "hcm"]):
        region = "TP. Hồ Chí Minh"
    elif any(k in q for k in ["đà nẵng", "da nang"]):
        region = "Đà Nẵng"
    elif any(k in q for k in ["hải phòng", "hai phong"]):
        region = "Hải Phòng"
    elif any(k in q for k in ["nha trang"]):
        region = "Nha Trang"
    elif any(k in q for k in ["phú quốc", "phu quoc"]):
        region = "Phú Quốc"
    elif any(k in q for k in ["quảng ninh", "hạ long", "ha long"]):
        region = "Hạ Long"

    facility_keywords = [
        "bệnh viện", "cơ sở", "phòng khám", "ở đâu", "chỗ nào", "nơi nào",
        "khám ở", "viện nào", "địa chỉ", "chi nhánh"
    ]
    # Bỏ qua nếu là câu hỏi về thông tin / địa chỉ cá nhân của người dùng
    if any(p in q for p in ["của tôi", "cua toi", "của mình", "cua minh", "thông tin cá nhân", "thong tin ca nhan"]):
        if not any(k in q for k in ["bệnh viện", "benh vien", "phòng khám", "phong kham", "cơ sở", "co so", "vinmec"]):
            return False, None

    is_asking_facility = any(k in q for k in facility_keywords)
    return is_asking_facility, region
