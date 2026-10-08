"""
Dynamic Clinical Probing Service (Vòng lặp hỏi bệnh chủ động)
Giải quyết bài toán: Bệnh nhân mô tả triệu chứng chung chung (VD: 'đau đầu', 'đau bụng', 'đau ngực')
-> Agent chủ động đặt câu hỏi làm rõ vị trí, thời gian, mức độ, triệu chứng đi kèm.
-> Tối đa 2-3 lượt hỏi, nếu bệnh nhân không biết trả lời thì tự động dừng và điều hướng theo dữ kiện sẵn có.
"""

from typing import Any

from pydantic import BaseModel

from src.medical_assistant.domain.language_service import detect_language


class ProbingClarificationTree(BaseModel):
    category_key: str
    trigger_keywords: list[str]
    # Lượt 1: Hỏi vị trí và tính chất (Vị trí đau, cảm giác đau)
    turn_1_question_vi: str
    turn_1_question_en: str
    turn_1_quick_replies_vi: list[str]
    turn_1_quick_replies_en: list[str]
    # Lượt 2: Hỏi triệu chứng đi kèm nguy hiểm
    turn_2_question_vi: str
    turn_2_question_en: str
    turn_2_quick_replies_vi: list[str]
    turn_2_quick_replies_en: list[str]


# Cây quyết định hỏi bệnh lâm sàng chuẩn y tế cho các triệu chứng hay gặp (Bilingual EN-VI)
CLINICAL_PROBING_TREES: list[ProbingClarificationTree] = [
    ProbingClarificationTree(
        category_key="TAO_BON",
        trigger_keywords=[
            "táo bón",
            "khó đi ngoài",
            "không đi ngoài",
            "phân cứng",
            "constipation",
            "hard stool",
            "unable to pass stool",
        ],
        turn_1_question_vi=(
            "Dạ, để đánh giá tình trạng táo bón của bác, bác cho em biết thêm:\n"
            "- Bác đã bị bao lâu và mấy ngày rồi chưa đi ngoài?\n"
            "- Phân có khô cứng, phải rặn nhiều hoặc vẫn trung tiện được không ạ?"
        ),
        turn_1_question_en=(
            "To assess the constipation more safely, could you clarify:\n"
            "- How long has this been happening, and when was your last bowel movement?\n"
            "- Are the stools hard, do you need to strain, and can you still pass gas?"
        ),
        turn_1_quick_replies_vi=[
            "Mới bị 1-2 ngày",
            "Đã trên 3 ngày chưa đi ngoài",
            "Phân khô cứng, phải rặn",
            "Không trung tiện được",
        ],
        turn_1_quick_replies_en=[
            "Started 1-2 days ago",
            "No bowel movement for over 3 days",
            "Hard stool with straining",
            "Unable to pass gas",
        ],
        turn_2_question_vi=(
            "Bác có dấu hiệu nào kèm theo không ạ: đau bụng tăng nhiều, bụng chướng căng, "
            "nôn ói, sốt, đi ngoài ra máu hoặc sụt cân không chủ ý?"
        ),
        turn_2_question_en=(
            "Do you have worsening abdominal pain, marked bloating, vomiting, fever, "
            "blood in the stool, or unintentional weight loss?"
        ),
        turn_2_quick_replies_vi=[
            "Có đau bụng/chướng bụng nhiều",
            "Có nôn hoặc sốt",
            "Có máu trong phân",
            "Không có dấu hiệu trên",
        ],
        turn_2_quick_replies_en=["Severe pain or bloating", "Vomiting or fever", "Blood in stool", "None of these"],
    ),
    ProbingClarificationTree(
        category_key="DAU_DAU",
        trigger_keywords=[
            "đau đầu",
            "nhức đầu",
            "nặng đầu",
            "chóng mặt",
            "đau nửa đầu",
            "buốt đầu",
            "headache",
            "dizziness",
            "migraine",
            "head pain",
        ],
        turn_1_question_vi=(
            "Bác cho em hỏi cụ thể hơn một chút ạ:\n"
            "- Cơn đau đầu của bác xuất hiện ở vị trí nào (đau nửa đầu bên trái/phải, sau gáy hay đau cả đầu)?\n"
            "- Cơn đau này đã kéo dài bao lâu rồi ạ (mới bị vài giờ hay đau âm ỉ nhiều tuần)?"
        ),
        turn_1_question_en=(
            "Could you provide a few more details regarding your headache:\n"
            "- Where is the pain located (one-sided, back of the neck, or all over)?\n"
            "- How long have you experienced this pain (sudden onset hours ago, or persistent for weeks)?"
        ),
        turn_1_quick_replies_vi=[
            "Đau nửa đầu trái/phải",
            "Đau sau gáy vùng cổ",
            "Đau cả đầu âm ỉ",
            "Mới đau đột ngột",
            "Đã đau nhiều tuần",
        ],
        turn_1_quick_replies_en=[
            "One-sided headache",
            "Back of neck/head",
            "Dull ache all over",
            "Sudden onset today",
            "Persistent for weeks",
        ],
        turn_2_question_vi=(
            "Dạ em đã ghi nhận vị trí đau. Bác có kèm theo dấu hiệu nào dưới đây không ạ:\n"
            "- Buồn nôn, sợ ánh sáng/tiếng ồn?\n"
            "- Mắt mờ, nhìn đôi hoặc tê yếu nửa mặt, tay chân không?"
        ),
        turn_2_question_en=(
            "Thank you. Are you experiencing any of the following accompanying symptoms:\n"
            "- Nausea, vomiting, or sensitivity to light/sound?\n"
            "- Blurred/double vision, facial numbness, or limb weakness?"
        ),
        turn_2_quick_replies_vi=[
            "Có buồn nôn / sợ ánh sáng",
            "Có nhìn mờ / tê tay chân",
            "Không có triệu chứng kèm theo",
            "Không chắc chắn",
        ],
        turn_2_quick_replies_en=[
            "Nausea / light sensitive",
            "Blurred vision / numbness",
            "No accompanying symptoms",
            "Not sure",
        ],
    ),
    ProbingClarificationTree(
        category_key="DAU_BUNG",
        trigger_keywords=[
            "đau bụng",
            "nhức bụng",
            "quặn bụng",
            "đầy bụng",
            "chướng bụng",
            "khó tiêu",
            "bụng bên trái",
            "bụng bên phải",
            "bụng trái",
            "bụng phải",
            "abdominal pain",
            "stomach pain",
            "stomach ache",
            "indigestion",
            "cramping",
        ],
        turn_1_question_vi=(
            "Để hỗ trợ bác chuẩn xác nhất, bác có thể chia sẻ thêm:\n"
            "- Bác đau ở vùng nào trên bụng (vùng trên rốn, quanh rốn, hay vùng bụng dưới bên phải/trái)?\n"
            "- Cơn đau âm ỉ liên tục hay đau quặn thắt từng cơn ạ?"
        ),
        turn_1_question_en=(
            "To better guide your appointment, could you clarify:\n"
            "- Which area of the abdomen hurts (upper stomach, around navel, or lower right/left)?\n"
            "- Is the pain constant and dull, or severe and cramping?"
        ),
        turn_1_quick_replies_vi=[
            "Trên rốn (vùng dạ dày)",
            "Quanh rốn",
            "Bụng dưới bên phải",
            "Bụng dưới bên trái",
            "Đau quặn từng cơn",
        ],
        turn_1_quick_replies_en=[
            "Upper stomach (epigastric)",
            "Around the navel",
            "Lower right abdomen",
            "Lower left abdomen",
            "Cramping in waves",
        ],
        turn_2_question_vi=("Dạ, bác có kèm theo sốt, buồn nôn, đi ngoài phân lỏng, hoặc nôn ói nhiều không ạ?"),
        turn_2_question_en=("Are you also experiencing fever, nausea, persistent vomiting, or diarrhea?"),
        turn_2_quick_replies_vi=["Có sốt nhẹ / buồn nôn", "Có tiêu chảy / nôn", "Không có sốt hay nôn", "Không rõ"],
        turn_2_quick_replies_en=["Mild fever / nausea", "Diarrhea / vomiting", "No fever or vomiting", "Not sure"],
    ),
    ProbingClarificationTree(
        category_key="DAU_NGUC",
        trigger_keywords=[
            "tức ngực",
            "tức lồng ngực",
            "đau tức lồng ngực",
            "đau tức ngực",
            "nặng ngực",
            "nhói ngực",
            "đau ngực",
            "chest pain",
            "chest pressure",
            "chest tightness",
            "angina",
        ],
        turn_1_question_vi=(
            "Triệu chứng vùng ngực cần được theo dõi kỹ lưỡng ạ. Bác cho em hỏi:\n"
            "- Cơn đau có cảm giác đè nặng, bóp nghẹt hay chỉ nhói nhẹ khi đổi tư thế?\n"
            "- Cơn đau có lan ra cánh tay trái, sau lưng hoặc lên cằm không ạ?"
        ),
        turn_1_question_en=(
            "Chest symptoms require careful evaluation. Could you describe:\n"
            "- Is the pain a heavy crushing sensation, or a sharp pain when moving/breathing?\n"
            "- Does the pain radiate to your left arm, back, or jaw?"
        ),
        turn_1_quick_replies_vi=[
            "Đè nặng / bóp nghẹt",
            "Chỉ nhói nhẹ khi thở/xoay người",
            "Có lan ra cánh tay / cằm",
            "Không lan",
        ],
        turn_1_quick_replies_en=[
            "Heavy / crushing pressure",
            "Sharp with breathing/movement",
            "Radiating to arm/jaw",
            "No radiation",
        ],
        turn_2_question_vi=(
            "Bác có cảm thấy khó thở, vã mồ hôi lạnh, hoặc cơn đau tăng khi đi bộ/vận động gắng sức không ạ?"
        ),
        turn_2_question_en=(
            "Do you feel shortness of breath, cold sweats, or does the pain worsen during exertion/walking?"
        ),
        turn_2_quick_replies_vi=["Có khó thở / vã mồ hôi", "Đau khi gắng sức", "Không khó thở", "Không rõ"],
        turn_2_quick_replies_en=[
            "Short of breath / sweating",
            "Worse with exertion",
            "No breathing difficulty",
            "Not sure",
        ],
    ),
    ProbingClarificationTree(
        category_key="CO_XUONG_KHOP",
        trigger_keywords=[
            "đau đầu gối",
            "đau gối",
            "khớp gối",
            "mỏi gối",
            "sưng đầu gối",
            "đau lưng",
            "mỏi gáy",
            "đau khớp",
            "mỏi vai",
            "tê tay",
            "tê chân",
            # Cơ - Chi dưới / Chi trên
            "bắp đùi",
            "đau đùi",
            "cơ đùi",
            "đau cơ đùi",
            "đau bắp đùi",
            "bắp chân",
            "đau bắp chân",
            "đau cẳng chân",
            "cẳng chân",
            "đau cơ",
            "đau cơ bắp",
            "đau chân",
            "đau bắp tay",
            "cơ bắp",
            "knee pain",
            "back pain",
            "neck pain",
            "joint pain",
            "shoulder pain",
            "numbness",
            "thigh pain",
            "muscle pain",
            "leg pain",
            "calf pain",
            "muscle ache",
            "sore muscles",
        ],
        turn_1_question_vi=(
            "Bác có thể mô tả rõ hơn:\n"
            "- Vị trí đau nhức nhiều nhất ở bắp đùi/cẳng chân, khớp gối, cổ vai gáy hay cột sống thắt lưng?\n"
            "- Cơn đau có kèm cảm giác tê buốt lan dọc xuống cẳng tay hoặc bàn chân không ạ?"
        ),
        turn_1_question_en=(
            "Could you specify:\n"
            "- Where is the discomfort most pronounced (thigh/calf, knee joints, neck/shoulders, or spine)?\n"
            "- Does the pain radiate with numbness down your arm or leg?"
        ),
        turn_1_quick_replies_vi=[
            "Bắp đùi / Cẳng chân",
            "Khớp gối",
            "Cột sống thắt lưng",
            "Cổ vai gáy",
            "Có tê lan xuống tay/chân",
            "Không tê lan",
        ],
        turn_1_quick_replies_en=[
            "Thigh / Calf",
            "Knee joints",
            "Lower back (lumbar)",
            "Neck and shoulders",
            "Radiating numbness to limbs",
            "No numbness",
        ],
        turn_2_question_vi=(
            "Cơn đau của bác tăng nhiều khi ngồi lâu, làm việc hay lúc sáng sớm ngủ dậy bị cứng khớp ạ?"
        ),
        turn_2_question_en=(
            "Does the discomfort worsen after prolonged sitting/working, or do you experience morning joint stiffness?"
        ),
        turn_2_quick_replies_vi=[
            "Cứng khớp buổi sáng",
            "Đau khi ngồi làm việc lâu",
            "Đau liên tục cả ngày",
            "Không rõ",
        ],
        turn_2_quick_replies_en=[
            "Morning stiffness",
            "Worse after sitting long",
            "Continuous pain all day",
            "Not sure",
        ],
    ),
]


class DynamicProbingService:
    """Service điều phối vòng lặp hỏi bệnh chủ động (Bilingual EN-VI)"""

    COMPLAINT_CATEGORY_MAP = {
        "constipation": "TAO_BON",
        "headache": "DAU_DAU",
        "abdominal_pain": "DAU_BUNG",
        "chest_pain": "DAU_NGUC",
        "back_pain": "CO_XUONG_KHOP",
        "joint_pain": "CO_XUONG_KHOP",
        "neck_pain": "CO_XUONG_KHOP",
        # Cơ - Chi dưới / Chi trên
        "muscle_pain": "CO_XUONG_KHOP",
        "leg_pain": "CO_XUONG_KHOP",
        "thigh_pain": "CO_XUONG_KHOP",
        "neck_shoulder_pain": "CO_XUONG_KHOP",
    }

    def find_all_probing_trees(self, text: str) -> list[ProbingClarificationTree]:
        """Return every non-negated probing tree mentioned in one utterance."""
        text_lower = text.lower()
        from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service

        negation_svc = get_clinical_negation_service()
        matches: list[ProbingClarificationTree] = []
        seen: set[str] = set()
        for tree in CLINICAL_PROBING_TREES:
            if tree.category_key in seen:
                continue
            for keyword in tree.trigger_keywords:
                # Tránh nhận nhầm "đau đầu" khi câu nói là "đau đầu gối" (khớp gối)
                if keyword in {"đau đầu", "nhức đầu"} and ("đau đầu gối" in text_lower or "nhức đầu gối" in text_lower):
                    continue
                if keyword in text_lower and not negation_svc.is_phrase_negated(keyword, text):
                    matches.append(tree)
                    seen.add(tree.category_key)
                    break
        return matches

    def sync_probing_state(
        self,
        clinical_facts: dict[str, Any] | None,
        existing: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Keep an independent probing budget for each active complaint."""
        synced: dict[str, dict[str, Any]] = {
            code: dict(value) for code, value in (existing or {}).items() if isinstance(value, dict)
        }
        for complaint in (clinical_facts or {}).get("complaints") or []:
            if isinstance(complaint, str):
                code, status = complaint, "active"
            else:
                code = str(complaint.get("code") or "")
                status = str(complaint.get("status") or "active")
            if not code:
                continue
            category = self.COMPLAINT_CATEGORY_MAP.get(code)
            previous = synced.get(code, {})
            synced[code] = {
                "category": category,
                "status": status,
                "questions_asked": int(previous.get("questions_asked") or 0),
            }
        return synced

    @staticmethod
    def active_categories(probing_by_complaint: dict[str, dict[str, Any]]) -> list[str]:
        categories: list[str] = []
        for item in probing_by_complaint.values():
            category = item.get("category")
            if item.get("status") == "active" and category and category not in categories:
                categories.append(category)
        return categories

    @staticmethod
    def mark_multi_question_asked(
        probing_by_complaint: dict[str, dict[str, Any]],
        complaint_codes: list[str],
    ) -> dict[str, dict[str, Any]]:
        updated = {code: dict(value) for code, value in probing_by_complaint.items()}
        for code in complaint_codes:
            if code in updated and updated[code].get("status") == "active":
                updated[code]["questions_asked"] = min(
                    2,
                    int(updated[code].get("questions_asked") or 0) + 1,
                )
        return updated

    @staticmethod
    def should_ask_multi_question(probing_by_complaint: dict[str, dict[str, Any]]) -> bool:
        active = [item for item in probing_by_complaint.values() if item.get("status") == "active"]
        return len(active) >= 2 and any(int(item.get("questions_asked") or 0) == 0 for item in active)

    def get_probing_candidates_for_context(
        self,
        chief_complaint: str | None,
        language: str = "vi",
        active_categories: list[str] | None = None,
    ) -> list[str]:
        """Return candidate probing questions for the active clinical complaint/categories."""
        target_cats: list[str] = []
        if chief_complaint and chief_complaint in self.COMPLAINT_CATEGORY_MAP:
            target_cats.append(self.COMPLAINT_CATEGORY_MAP[chief_complaint])
        if active_categories:
            for cat in active_categories:
                if cat not in target_cats:
                    target_cats.append(cat)

        candidates: list[str] = []
        for tree in CLINICAL_PROBING_TREES:
            if tree.category_key in target_cats:
                q1 = tree.turn_1_question_en if language == "en" else tree.turn_1_question_vi
                q2 = tree.turn_2_question_en if language == "en" else tree.turn_2_question_vi
                candidates.extend([q1, q2])
        return candidates

    def find_probing_tree(self, text: str) -> ProbingClarificationTree | None:
        matches = self.find_all_probing_trees(text)
        return matches[0] if matches else None

    def get_next_question(
        self,
        user_message: str,
        probing_turn: int,
        active_category: str | None = None,
        language: str | None = None,
        clinical_facts: dict[str, Any] | None = None,
    ) -> tuple[str, list[str], str] | None:
        """
        Trả về: (Câu hỏi, Danh sách gợi ý trả lời nhanh, Category Key)
        Nếu probing_turn >= 2 hoặc người dùng nói 'không biết / thôi' -> Trả về None (dừng hỏi, chốt kết quả)
        """
        user_lower = user_message.lower()
        lang = language if language in ["vi", "en"] else detect_language(user_message)

        # Kiểm tra nếu bệnh nhân không muốn trả lời hoặc không biết
        stop_keywords = [
            "không biết",
            "không rõ",
            "bỏ qua",
            "không nói được",
            "thôi",
            "đặt luôn",
            "skip",
            "dont know",
            "not sure",
            "pass",
            "no idea",
            "just book",
        ]
        if any(w in user_lower for w in stop_keywords):
            return None

        # Nếu đã hỏi đủ 2 lượt -> Dừng vòng lặp để chốt đặt lịch
        if probing_turn >= 2:
            return None

        tree = None
        if active_category:
            for t in CLINICAL_PROBING_TREES:
                if t.category_key == active_category:
                    tree = t
                    break
        if not tree:
            tree = self.find_probing_tree(user_message)

        if not tree:
            return None

        # Với táo bón, tạo câu hỏi từ dữ kiện còn thiếu thay vì lặp nguyên cây cố định.
        if tree.category_key == "TAO_BON" and clinical_facts:
            positive = set(clinical_facts.get("positive_facts") or [])
            negative = set(clinical_facts.get("negative_facts") or [])
            known = positive | negative
            missing_initial = []
            if clinical_facts.get("duration_days") is None:
                missing_initial.append("tình trạng này bắt đầu từ bao lâu")
            if clinical_facts.get("bowel_interval_days") is None:
                missing_initial.append("lần đi ngoài gần nhất là khi nào")
            if not ({"hard_stool", "straining"} & known):
                missing_initial.append("phân có khô cứng hoặc phải rặn nhiều không")
            if not ({"passing_gas", "unable_to_pass_gas"} & known):
                missing_initial.append("bác có còn trung tiện được không")

            red_flag_labels = {
                "blood_in_stool": "có thấy máu khi đi ngoài",
                "weight_loss": "có sụt cân không chủ ý",
                "vomiting": "có nôn ói",
                "fever": "có sốt",
                "severe_abdominal_pain": "đau bụng có tăng nhiều hoặc quặn dữ dội",
            }
            missing_red_flags = [label for fact, label in red_flag_labels.items() if fact not in known]

            if probing_turn == 0 and missing_initial:
                prompts = missing_initial[:2]
                if len(prompts) == 1 and missing_red_flags:
                    prompts.append(missing_red_flags[0])
                question = (
                    "Dạ, em đã ghi nhận các thông tin bác vừa cung cấp. Em chỉ cần làm rõ thêm: "
                    + "; ".join(prompts)
                    + " ạ?"
                )
                replies = ["Trả lời chi tiết", "Không rõ", "Bỏ qua để xem hướng khám"]
                return question, replies, tree.category_key

            if missing_red_flags:
                prompts = missing_red_flags[:2]
                question = (
                    "Dạ, em không hỏi lại các thông tin đã có. Bác cho em xác nhận thêm: "
                    + " và ".join(prompts)
                    + " không ạ?"
                )
                replies = ["Có một trong các dấu hiệu trên", "Không có", "Không rõ"]
                return question, replies, tree.category_key

            return None

        # Với đau đầu, bỏ qua các câu hỏi về vị trí/thời gian nếu người bệnh đã cung cấp
        if tree.category_key == "DAU_DAU" and clinical_facts:
            positive = set(clinical_facts.get("positive_facts") or [])
            negative = set(clinical_facts.get("negative_facts") or [])
            known = positive | negative

            has_location = bool({"one_sided_headache"} & known) or bool(clinical_facts.get("location"))
            has_duration = clinical_facts.get("duration_days") is not None

            neuro_red_flag_labels = {
                "nausea": "buồn nôn hoặc nôn",
                "vision_changes": "nhìn mờ hoặc nhìn đôi",
                "numbness_weakness": "tê yếu nửa mặt/tay chân",
                "fever": "sốt",
            }
            missing_neuro_flags = [label for fact, label in neuro_red_flag_labels.items() if fact not in known]

            if probing_turn == 0:
                if has_location and has_duration:
                    if missing_neuro_flags:
                        prompts = missing_neuro_flags[:2]
                        if lang == "en":
                            q = "Thank you. Do you have any accompanying symptoms: " + " or ".join(prompts) + "?"
                            qr = ["Yes, experiencing some", "No accompanying symptoms", "Not sure"]
                        else:
                            q = (
                                "Dạ, em đã ghi nhận vị trí và thời gian đau. Bác cho em xác nhận thêm: bác có kèm theo "
                                + " hoặc ".join(prompts)
                                + " không ạ?"
                            )
                            qr = ["Có một trong các dấu hiệu trên", "Không có", "Không rõ"]
                        return q, qr, tree.category_key
                    return None
            elif probing_turn == 1:
                if missing_neuro_flags:
                    prompts = missing_neuro_flags[:2]
                    if lang == "en":
                        q = "Do you experience: " + " or ".join(prompts) + "?"
                        qr = ["Yes", "No", "Not sure"]
                    else:
                        q = "Bác có kèm theo: " + " hoặc ".join(prompts) + " không ạ?"
                        qr = ["Có dấu hiệu trên", "Không có", "Không rõ"]
                    return q, qr, tree.category_key
                return None

        # Với đau bụng, kiểm tra cờ đỏ tiêu hóa còn thiếu
        if tree.category_key == "DAU_BUNG" and clinical_facts:
            positive = set(clinical_facts.get("positive_facts") or [])
            negative = set(clinical_facts.get("negative_facts") or [])
            known = positive | negative

            gi_red_flag_labels = {
                "vomiting": "nôn ói nhiều",
                "fever": "sốt",
                "diarrhea": "tiêu chảy",
                "blood_in_stool": "đi ngoài ra máu",
            }
            missing_gi_flags = [label for fact, label in gi_red_flag_labels.items() if fact not in known]

            pain_nature_known = bool({"mild_abdominal_pain", "severe_abdominal_pain"} & known)
            if probing_turn == 0 and clinical_facts.get("location") and pain_nature_known:
                prompts = []
                if clinical_facts.get("duration_days") is None:
                    prompts.append("tình trạng này kéo dài chính xác bao lâu")
                prompts.extend(missing_gi_flags[: max(0, 3 - len(prompts))])
                if not prompts:
                    return None
                if lang == "en":
                    q = "I've noted the pain location and nature. Could you clarify " + ", ".join(prompts) + "?"
                    qr = ["Started today", "Several days", "None of those warning signs", "Not sure"]
                else:
                    q = (
                        "Dạ, em đã ghi nhận vị trí và tính chất đau. Bác cho em biết thêm "
                        + ", ".join(prompts)
                        + " không ạ?"
                    )
                    qr = ["Mới đau hôm nay", "Đã đau vài ngày", "Không có dấu hiệu kèm theo", "Không rõ"]
                return q, qr, tree.category_key

            if probing_turn == 0 and clinical_facts.get("location"):
                if lang == "en":
                    q = "I've noted the pain location. Is the pain dull and continuous or cramping, and how severe is it from 0 to 10?"
                    qr = ["Dull and continuous", "Cramping in waves", "Severe pain", "Not sure"]
                else:
                    q = "Dạ, em đã ghi nhận vị trí đau. Cơn đau âm ỉ liên tục hay quặn từng cơn, và mức độ khoảng bao nhiêu trên thang 0–10 ạ?"
                    qr = ["Đau âm ỉ liên tục", "Đau quặn từng cơn", "Đau nhiều", "Không rõ"]
                return q, qr, tree.category_key

            if probing_turn == 1:
                if missing_gi_flags:
                    prompts = missing_gi_flags[:2]
                    if lang == "en":
                        q = "Are you experiencing any accompanying symptoms: " + " or ".join(prompts) + "?"
                        qr = ["Yes", "No", "Not sure"]
                    else:
                        q = (
                            "Dạ, em đã ghi nhận tính chất đau bụng. Bác có kèm theo "
                            + " hoặc ".join(prompts)
                            + " không ạ?"
                        )
                        qr = ["Có dấu hiệu trên", "Không có", "Không rõ"]
                    return q, qr, tree.category_key
                return None

        # Với cơ xương khớp, bỏ qua câu hỏi vị trí/thời gian nếu người bệnh đã cung cấp
        if tree.category_key == "CO_XUONG_KHOP" and clinical_facts:
            positive = set(clinical_facts.get("positive_facts") or [])
            negative = set(clinical_facts.get("negative_facts") or [])
            known = positive | negative

            has_location = bool(
                clinical_facts.get("location")
                or any(
                    w in user_lower
                    for w in [
                        "bắp đùi",
                        "đùi",
                        "cơ đùi",
                        "bắp chân",
                        "cẳng chân",
                        "đầu gối",
                        "khớp gối",
                        "gối",
                        "lưng",
                        "vai gáy",
                        "cổ vai gáy",
                        "cột sống",
                        "thắt lưng",
                        "cổ chân",
                        "bàn chân",
                    ]
                )
            )
            has_duration = clinical_facts.get("duration_days") is not None or any(
                w in user_lower for w in ["ngày", "tuần", "tháng", "hôm nay", "hôm qua", "bữa"]
            )

            msk_red_flag_labels = {
                "trauma": "chấn thương, ngã hoặc va đập mạnh trước đó",
                "numbness_weakness": "tê buốt lan xuống bàn chân hoặc yếu cơ",
                "joint_swelling": "sưng, nóng, đỏ tại vùng đau",
                "fever": "sốt",
            }
            missing_msk_flags = [label for fact, label in msk_red_flag_labels.items() if fact not in known]

            if probing_turn == 0 and has_location:
                loc_desc = clinical_facts.get("location") or "vùng đau"
                if lang == "en":
                    loc_desc_en = clinical_facts.get("location") or "the affected area"
                    q = (
                        f"I've noted the discomfort at {loc_desc_en}. "
                        "Could you clarify if the pain started after trauma/injury, and if you have radiating numbness down your leg or localized swelling?"
                    )
                    qr = [
                        "After injury/strain",
                        "Radiating numbness to leg",
                        "Localized swelling/redness",
                        "None of these",
                    ]
                else:
                    q = (
                        f"Dạ, em đã ghi nhận vị trí và tính chất đau ({loc_desc}). "
                        "Bác cho em hỏi thêm: cơn đau xuất hiện sau chấn thương/vận động nặng không, và có kèm sưng đỏ hay cảm giác tê buốt lan xuống bàn chân không ạ?"
                    )
                    qr = [
                        "Sau va đập / vận động nặng",
                        "Có tê lan xuống chân",
                        "Vùng đau sưng đỏ",
                        "Không có dấu hiệu trên",
                    ]
                return q, qr, tree.category_key

            if probing_turn == 1:
                if missing_msk_flags:
                    prompts = missing_msk_flags[:2]
                    if lang == "en":
                        q = "Do you experience: " + " or ".join(prompts) + "?"
                        qr = ["Yes, experiencing some", "No", "Not sure"]
                    else:
                        q = "Dạ, bác cho em xác nhận thêm có kèm: " + " hoặc ".join(prompts) + " không ạ?"
                        qr = ["Có dấu hiệu trên", "Không có", "Không rõ"]
                    return q, qr, tree.category_key
                return None

        if probing_turn == 0:
            q = tree.turn_1_question_en if lang == "en" else tree.turn_1_question_vi
            qr = tree.turn_1_quick_replies_en if lang == "en" else tree.turn_1_quick_replies_vi
            return q, qr, tree.category_key
        elif probing_turn == 1:
            q = tree.turn_2_question_en if lang == "en" else tree.turn_2_question_vi
            qr = tree.turn_2_quick_replies_en if lang == "en" else tree.turn_2_quick_replies_vi
            return q, qr, tree.category_key

        return None


# Singleton
_probing_service = DynamicProbingService()


def get_probing_service() -> DynamicProbingService:
    return _probing_service
