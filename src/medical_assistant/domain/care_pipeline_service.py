"""
Staged Care Navigation Pipeline Service (Clinical Anatomical Priority Engine)
Chuyên trách giải quyết bài toán:
- Người bệnh mô tả triệu chứng thuộc 2 hoặc nhiều chuyên khoa khác nhau.
- Vạch ra lộ trình (Pipeline) khám phân tầng: Bước 1 khám khoa nào trước, Bước 2 khám khoa nào sau.
- Áp dụng nguyên tắc vàng y khoa:
  "Vị trí giải phẫu cơ quan sinh tồn luôn được ưu tiên trước mức độ đau đơn thuần"
  (Đau ngực/tim/não âm ỉ vẫn PHẢI khám trước đau khớp/răng dữ dội).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from pydantic import BaseModel


class CarePipelineStep(BaseModel):
    step_number: int
    department_name: str
    department_code: str
    target_symptoms: list[str]
    anatomical_rank: int  # 1: Sinh tồn (Tim/Não/Phổi), 2: Nội tạng chính (Tiêu hóa/Tiết niệu), 3: Ngoại vi
    clinical_rationale: str


class StagedCarePipeline(BaseModel):
    is_multi_specialty: bool
    primary_department: str
    secondary_departments: list[str]
    pipeline_steps: list[CarePipelineStep]
    formatted_guidance: str


# Bảng trọng số giải phẫu sinh tồn (Anatomical Vital Hierarchy)
ANATOMICAL_SYSTEMS = {
    # Hạng 1: Cơ quan sinh tồn tối khẩn (Vital Organs) - Weight: 90 - 100
    "TIM_MACH": {
        "weight": 95,
        "name": "Trung tâm Tim mạch",
        "organ_name": "Tim mạch & Tuần hoàn lồng ngực",
        "patterns": [
            r"\b(?:trai\s+tim|dau\s+tim|nhoi\s+tim|benh\s+tim|tim\s+mach|khoa\s+tim|nhip\s+tim|danh\s+trong\s+nguc|tim\s+dap|suy\s+tim|van\s+tim|co\s+tim|mach\s+vanh|tuc\s+nguc|tuc\s+nghen\s+nguc|dau\s+nguc|nang\s+nguc|that\s+nguc|long\s+nguc.*de\s+nang|de\s+nang|hoi\s+hop|loan\s+nhip|huyet\s+ap|1[6789]0\/|200\/|ke\s+cao\s+goi\s+moi\s+tho)\b"
        ],
        "rationale": "Cơ quan tuần hoàn sinh tồn tối khẩn; cần thăm khám trước để loại trừ thiếu máu cơ tim, nhồi máu cơ tim hoặc cơn tăng huyết áp kịch phát đe dọa tính mạng.",
    },
    "THAN_KINH": {
        "weight": 90,
        "name": "Khoa Thần kinh",
        "organ_name": "Não bộ & Hệ thần kinh trung ương",
        "patterns": [
            r"\b(?:dau\s+dau(?!\s+goi)|nhuc\s+dau(?!\s+goi)|nua\s+dau|chong\s+mat|choang\s+ngat|choang\s+vang|tien\s+ngat|ngat\s+thoang\s+qua|yeu\s+tay|yeu\s+chan|tay.*yeu|yeu.*tay|cam\s+dua.*roi|yeu\s+chi|yeu\s+nua\s+nguoi|sup\s+mi|meo\s+mieng|noi\s+do|co\s+giat|day\s+than\s+kinh|quay\s+cuong|dien\s+giat|nua\s+mat)\b"
        ],
        "rationale": "Não bộ và hệ thần kinh trung ương kiểm soát toàn bộ cơ thể; cần ưu tiên đánh giá sớm để loại trừ đột quỵ, cơn thiếu máu não thoáng qua hoặc tổn thương nội sọ.",
    },
    "HO_HAP": {
        "weight": 85,
        "name": "Khoa Nội hô hấp",
        "organ_name": "Đường thở & Chức năng trao đổi khí phổi",
        "patterns": [
            r"\b(?:kho\s+tho|hut\s+hoi|tho\s+rit|tho\s+khe|kho\s+khe|ho.*ra\s+mau|khac.*ra\s+mau|ho\s+khac|vet\s+mau|dom\s+mau|ho\s+khac\s+dom|dom\s+vang|sot\s+39|viem\s+phoi|viem\s+phe\s+quan)\b"
        ],
        "rationale": "Đường thở và chức năng thông khí cung cấp oxy duy trì sự sống; cần được ưu tiên kiểm tra trước các cơ quan ngoại vi.",
    },
    "UNG_BUOU": {
        "weight": 80,
        "name": "Trung tâm Ung bướu",
        "organ_name": "Bệnh lý ác tính & Hạch khối u",
        "patterns": [
            r"\b(?:k\s+giap|k\s+vu|k\s+phoi|k\s+gan|ung\s+thu|u\s+ac|di\s+can|hach\s+co|hach\s+nach|hach\s+cung|khoi\s+u|cuc\s+hach)\b"
        ],
        "rationale": "Bệnh lý nghi ngờ ác tính/ung bướu cần ưu tiên tầm soát và đánh giá giai đoạn sớm để có chiến lược điều trị kịp thời.",
    },
    # Hạng 2: Cơ quan nội tạng quan trọng (Major Internal Organs) - Weight: 50 - 70
    "SAN_PHU_KHOA": {
        "weight": 70,
        "name": "Khoa Sản phụ khoa",
        "organ_name": "Cơ quan sinh sản & Thai nghén cấp",
        "patterns": [
            r"\b(?:tre\s+kinh|cham\s+kinh|ra\s+mau\s+am\s+dao|ra\s+huyet|thai\s+ngoai|dau\s+bung\s+duoi|phu\s+khoa)\b"
        ],
        "rationale": "Biến chứng thai nghén cấp (như thai ngoài tử cung) là cấp cứu đe dọa sinh mạng người phụ nữ, cần được loại trừ ngay.",
    },
    "TIEU_HOA": {
        "weight": 65,
        "name": "Khoa Tiêu hóa - Gan mật",
        "organ_name": "Hệ tiêu hóa & Gan mật",
        "patterns": [
            r"\b(?:dau\s+bung|thuong\s+vi|ha\s+suon|phan\s+den|non\s+ra\s+mau|tieu\s+chay|day\s+bung|o\s+chua|o\s+hoi|trao\s+nguoc|tao\s+bon|nuot\s+nghen|nghen\s+o\s+co\s+hong)\b"
        ],
        "rationale": "Cơ quan tiêu hóa nội tạng; cần đánh giá để loại trừ xuất huyết tiêu hóa, viêm tụy cấp hoặc bệnh lý ngoại khoa.",
    },
    "THAN_TIET_NIEU": {
        "weight": 60,
        "name": "Khoa Thận - Tiết niệu",
        "organ_name": "Hệ thận & Đường tiết niệu",
        "patterns": [
            r"\b(?:tieu\s+buot|tieu\s+rat|tieu\s+mau|nuoc\s+tieu\s+do|tieu\s+it|phu\s+chan|phu\s+mat|soi\s+than|suy\s+than|viem\s+than|quan\s+than)\b"
        ],
        "rationale": "Hệ thống lọc thải và chức năng thận; cần kiểm tra các nguyên nhân nhiễm trùng đường tiểu hoặc tổn thương cầu thận.",
    },
    "NOI_TIET": {
        "weight": 55,
        "name": "Khoa Nội tiết - Đái tháo đường",
        "organ_name": "Rối loạn chuyển hóa & Nội tiết",
        "patterns": [
            r"\b(?:khat\s+nuoc|tieu\s+dem|tieu\s+nhieu|dai\s+thao\s+duong|dtd|tuyen\s+giap|trieu\s+chung\s+noi\s+tiet)\b"
        ],
        "rationale": "Chuyển hóa và điều hòa đường huyết; cần kiểm soát rối loạn chuyển hóa toàn thân.",
    },
    # Hạng 3: Ngoại vi / Cơ xương khớp / Giác quan (Peripheral Systems) - Weight: 20 - 40
    "XUONG_KHOP": {
        "weight": 35,
        "name": "Khoa Chấn thương chỉnh hình & Cột sống",
        "organ_name": "Hệ vận động & Cơ xương khớp",
        "patterns": [
            r"\b(?:khop\s+goi|dau\s+dau\s+goi|dau\s+goi|dau\s+khop\s+goi|dau\s+khop|nhuc\s+khop|sung\s+khop|moi\s+khop|cung\s+khop|sung\s+dau\s+goi|dau\s+lung|that\s+lung|khop\s+vai|co\s+vai\s+gay|moi\s+co|dau\s+got|got\s+chan|ngon\s+chan|gut|gout|khop\s+ngon\s+tay)\b"
        ],
        "rationale": "Hệ cơ xương khớp ngoại vi; triệu chứng có thể gây đau buốt dữ dội nhưng thường ít đe dọa sinh mạng ngay tức thì so với các tạng sinh tồn.",
    },
    "TAI_MUI_HONG": {
        "weight": 30,
        "name": "Khoa Tai - Mũi - Họng",
        "organ_name": "Tai Mũi Họng & Tiền đình ngoại biên",
        "patterns": [
            r"\b(?:co\s+hong|dau\s+hong|rat\s+hong|dau\s+rat|nuot\s+vuong|ngat\s+mui|chay\s+mui|chay\s+nuoc\s+mui|u\s+tai|xoang|viem\s+amidan)\b"
        ],
        "rationale": "Đường hô hấp trên và cơ quan thính giác ngoại biên; thăm khám phối hợp điều trị triệu chứng tại chỗ.",
    },
    "MAT": {
        "weight": 25,
        "name": "Khoa Mắt",
        "organ_name": "Thị giác & Mắt",
        "patterns": [
            r"\b(?:moi\s+mat|mat\s+moi|mat\s+mo|mo\s+mat|nhin\s+mo|nhin\s+doi|com\s+mat|mat\s+do|ngua\s+mat|chay\s+nuoc\s+mat|dau\s+mat|kho\s+mat|nhan\s+khoa|thi\s+luc|can\s+thi|loan\s+thi|vien\s+thi|giam\s+thi\s+luc)\b"
        ],
        "rationale": "Cơ quan thị giác bề mặt; kiểm tra bảo tồn chức năng nhìn.",
    },
    "DA_LIEU": {
        "weight": 20,
        "name": "Khoa Da liễu",
        "organ_name": "Bề mặt da & Phần phụ",
        "patterns": [
            r"\b(?:man\s+ngua|ngua\s+da|noi\s+me\s+day|mun\s+boc|mun\s+viem|da\s+lieu|vay\s+nen|viem\s+da|ngua\s+khap\s+nguoi|ngua\s+do|vung\s+da.*ngua)\b"
        ],
        "rationale": "Tổn thương da liễu bề mặt; điều trị giảm triệu chứng ngứa và bảo vệ hàng rào bảo vệ cơ thể.",
    },
    "RANG_HAM_MAT": {
        "weight": 20,
        "name": "Khoa Răng - Hàm - Mặt",
        "organ_name": "Răng miệng & Vùng hàm mặt",
        "patterns": [r"\b(?:dau\s+rang|nhuc\s+rang|rang\s+sau|dau\s+tuy|viem\s+loi|nha\s+chu|rang\s+ham)\b"],
        "rationale": "Răng miệng và vùng hàm mặt; điều trị dứt điểm cơn đau buốt cục bộ.",
    },
}


class CarePipelineService:
    @staticmethod
    def normalize_text(text: str) -> str:
        folded = unicodedata.normalize("NFKD", text.casefold())
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        folded = folded.replace("đ", "d").replace("Đ", "d")
        return re.sub(r"\s+", " ", folded).strip()

    def evaluate_multi_specialty_pipeline(
        self,
        query: str,
        detected_specialties: list[str] | None = None,
        language: str = "vi",
    ) -> StagedCarePipeline:
        """
        Xây dựng lộ trình (Pipeline) khám 2 giai đoạn chuẩn y khoa khi người bệnh có triệu chứng nhiều khoa.
        Áp dụng Quy tắc Vị trí Giải phẫu Sinh tồn (Anatomical Priority).
        """
        from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service

        negation_svc = get_clinical_negation_service()

        clean_text = self.normalize_text(query)
        matched_systems: list[tuple[str, dict[str, Any], list[str]]] = []

        for sys_code, sys_data in ANATOMICAL_SYSTEMS.items():
            matched_terms: list[str] = []
            for pat in sys_data["patterns"]:
                for match in re.finditer(pat, clean_text):
                    m_str = match.group(0)
                    if not negation_svc.is_phrase_negated(m_str, query):
                        matched_terms.append(m_str)
            if matched_terms:
                matched_systems.append((sys_code, sys_data, list(set(matched_terms))))

        # Sắp xếp các khoa theo Trọng số Giải phẫu Sinh tồn (Giảm dần)
        matched_systems.sort(key=lambda item: item[1]["weight"], reverse=True)

        if len(matched_systems) < 2:
            primary_name = matched_systems[0][1]["name"] if matched_systems else "Nội đa khoa"
            return StagedCarePipeline(
                is_multi_specialty=False,
                primary_department=primary_name,
                secondary_departments=[],
                pipeline_steps=[],
                formatted_guidance="",
            )

        # Xây dựng các bước trong Pipeline khám
        steps: list[CarePipelineStep] = []
        for idx, (sys_code, sys_data, terms) in enumerate(matched_systems[:2], start=1):
            rank = 1 if sys_data["weight"] >= 80 else (2 if sys_data["weight"] >= 50 else 3)
            steps.append(
                CarePipelineStep(
                    step_number=idx,
                    department_name=sys_data["name"],
                    department_code=sys_code,
                    target_symptoms=terms,
                    anatomical_rank=rank,
                    clinical_rationale=sys_data["rationale"],
                )
            )

        step1 = steps[0]
        step2 = steps[1]

        # Sinh văn bản định hướng Pipeline rõ ràng, thuyết phục, chuẩn y khoa
        formatted_guidance = (
            f"🏥 **Lộ trình Khám Ưu tiên Phân tầng (Staged Care Navigation Pipeline):**\n\n"
            f"Dạ thưa bác, triệu chứng của bác xuất hiện đồng thời ở nhiều cơ quan khác nhau. "
            f"Trong y khoa, **vị trí cơ quan giải phẫu sinh tồn luôn được ưu tiên kiểm tra trước mức độ đau đơn thuần** "
            f"(triệu chứng ở tim, phổi, não bộ dù âm ỉ vẫn phải loại trừ trước các cơn đau buốt ở cơ xương khớp hay răng miệng).\n\n"
            f"Em xin vạch ra lộ trình thăm khám tối ưu nhất cho bác như sau:\n\n"
            f"• **📍 BƯỚC 1 (Khám ưu tiên trước): {step1.department_name}**\n"
            f"  - **Mục tiêu:** {step1.clinical_rationale}\n"
            f"  - **Lý do ưu tiên:** Cần thăm khám và thực hiện các xét nghiệm/chẩn đoán hình ảnh chuyên sâu để đảm bảo an toàn tuyệt đối cho cơ quan sinh tồn trước.\n\n"
            f"• **📍 BƯỚC 2 (Khám phối hợp kế tiếp): {step2.department_name}**\n"
            f"  - **Mục tiêu:** {step2.clinical_rationale}\n"
            f"  - **Lộ trình:** Sau khi bác sĩ ở Bước 1 đánh giá tình trạng đã ổn định hoặc loại trừ nguy cơ cấp tính, bác sẽ được kết hợp chuyển khám tại đây để điều trị dứt điểm triệu chứng kèm theo.\n\n"
            f"👉 Bác có muốn em hỗ trợ tìm bác sĩ và đặt lịch hẹn khám ưu tiên cho **{step1.department_name}** trước không ạ?"
        )

        return StagedCarePipeline(
            is_multi_specialty=True,
            primary_department=step1.department_name,
            secondary_departments=[s.department_name for s in steps[1:]],
            pipeline_steps=steps,
            formatted_guidance=formatted_guidance,
        )


_care_pipeline_service_instance: CarePipelineService | None = None


def get_care_pipeline_service() -> CarePipelineService:
    global _care_pipeline_service_instance
    if _care_pipeline_service_instance is None:
        _care_pipeline_service_instance = CarePipelineService()
    return _care_pipeline_service_instance
