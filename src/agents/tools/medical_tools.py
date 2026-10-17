"""Clinical and booking tools for LangGraph Agent."""

from typing import Any

from langchain_core.tools import tool


@tool
def calculate_bmi(weight_kg: float, height_cm: float) -> dict[str, Any]:
    """Tính chỉ số khối cơ thể (BMI) và phân loại tình trạng dinh dưỡng.

    Args:
        weight_kg: Cân nặng (kg)
        height_cm: Chiều cao (cm)

    Returns:
        Dictionary chứa giá trị BMI và phân loại theo chuẩn WHO/IDI & WPRO.
    """
    if height_cm <= 0 or weight_kg <= 0:
        return {"error": "Chiều cao và cân nặng phải lớn hơn 0"}
    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)
    if bmi < 18.5:
        category = "Gầy / Thiếu cân"
    elif bmi < 23.0:
        category = "Bình thường (chuẩn Châu Á)"
    elif bmi < 25.0:
        category = "Thừa cân / Tiền béo phì"
    elif bmi < 30.0:
        category = "Béo phì độ I"
    else:
        category = "Béo phì độ II trở lên"
    return {"bmi": bmi, "category": category}


@tool
def check_emergency_red_flags(symptoms: list[str]) -> dict[str, Any]:
    """Kiểm tra dấu hiệu cờ đỏ cấp cứu đe dọa tính mạng (ATS Level 1-2).

    Args:
        symptoms: Danh sách các triệu chứng người bệnh mô tả.

    Returns:
        Kết quả cảnh báo khẩn cấp và hướng dẫn xử trí 115.
    """
    red_flag_keywords = [
        "đau ngực dữ dội",
        "khó thở",
        "ngưng thở",
        "hôn mê",
        "co giật",
        "méo miệng",
        "liệt nửa người",
        "nôn ra máu",
        "bất tỉnh",
        "sốc phản vệ",
    ]
    detected = []
    text_corpus = " ".join(symptoms).lower()
    for flag in red_flag_keywords:
        if flag in text_corpus:
            detected.append(flag)
    is_emergency = len(detected) > 0
    return {
        "is_emergency": is_emergency,
        "detected_red_flags": detected,
        "recommendation": (
            "GỌI CẤP CỨU 115 NGAY LẬP TỨC hoặc đến phòng cấp cứu bệnh viện gần nhất!"
            if is_emergency
            else "Không phát hiện dấu hiệu cấp cứu tức thời."
        ),
    }
