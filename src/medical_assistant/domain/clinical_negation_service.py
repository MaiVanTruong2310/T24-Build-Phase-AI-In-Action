"""
Clinical Negation & Polarity Analysis Service
Xác định phạm vi phủ định (Negation Scope) và phân tách phân cực (Polarity) trong triệu chứng y tế.
Quy tắc:
- Nhận diện các từ chỉ sự phủ định (không, chưa, chẳng, chả, ko, k, no, not, without, denies...).
- Giới hạn phạm vi phủ định theo mệnh đề (kết thúc tại dấu câu hoặc liên từ đối lập: nhưng, tuy nhiên, song, còn...).
- Phân biệt triệu chứng khẳng định (Positive Fact) và triệu chứng phủ định (Negative Fact).
- Ngăn chặn triệt để hiện tượng Over-triage hoặc kích hoạt nhầm cờ đỏ khi người bệnh nói: "không đau ngực", "hết sốt rồi", "chưa từng ngất xỉu".
"""

import re
import unicodedata


class ClinicalNegationService:
    def __init__(self):
        # Từ khóa phủ định tiếng Việt (cả có dấu và không dấu)
        self.negation_patterns_vi = [
            r"\bkhông\s+còn\b",
            r"\bkhong\s+con\b",
            r"\bhết\b",
            r"\bhet\b",
            r"\bđâu\s+có\b",
            # Tránh va chạm với 'đau cổ' (đau cổ vai gáy) và 'đau cơ': chỉ khớp 'đâu có' không dấu khi đi kèm vị từ
            r"\bdau\s+co\s+(?:bi|thay|sot|phai|chua)\b",
            r"\bchẳng\b",
            r"\bchang\b",
            r"\bchả\b",
            r"\bcha\b",
            r"\bchưa\s+từng\b",
            r"\bchua\s+tung\b",
            r"\bchưa\s+bị\b",
            r"\bchua\s+bi\b",
            r"\bchưa\b",
            r"\bchua\b",
            r"\bkhông\b",
            r"\bkhong\b",
            r"\bko\b",
            r"\bk\b",
        ]

        # Từ khóa phủ định tiếng Anh
        self.negation_patterns_en = [
            r"\bdenies\b",
            r"\bdenied\b",
            r"\bnegative\s+for\b",
            r"\bfree\s+of\b",
            r"\bwithout\b",
            r"\bnever\b",
            r"\bnot\b",
            r"\bno\b",
            r"\bnone\b",
        ]

        # Liên từ / ranh giới ngắt phạm vi phủ định (Boundaries)
        self.boundary_pattern = re.compile(
            r"([.,;!?\n]|\b(?:nhưng|tuy\s+nhiên|song|còn|mà|chứ|nhung|tuy\s+nhien|con|ma|chu|but|however|although|yet|except|instead)\b)",
            re.IGNORECASE,
        )

        self.pseudo_negations = [
            r"\bkhông\s+rõ\b",
            r"\bkhong\s+ro\b",
            r"\bkhông\s+biết\b",
            r"\bkhong\s+biet\b",
            r"\bkhông\s+chắc\b",
            r"\bkhong\s+chac\b",
            r"\bchưa\s+rõ\b",
            r"\bchua\s+ro\b",
            r"\bchưa\s+biết\b",
            r"\bchua\s+biet\b",
            r"\bnot\s+sure\b",
            r"\bnot\s+certain\b",
        ]
        self._pseudo_regex = re.compile("|".join(self.pseudo_negations), re.IGNORECASE)

        self._all_negation_regex = re.compile(
            r"(" + "|".join(self.negation_patterns_vi + self.negation_patterns_en) + r")", re.IGNORECASE
        )

    @staticmethod
    def _normalize_ascii(text: str) -> str:
        """Chuẩn hóa loại bỏ dấu tiếng Việt để so khớp dung sai cao."""
        text = text.lower().strip()
        nfd = unicodedata.normalize("NFD", text)
        no_accent = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
        no_accent = no_accent.replace("đ", "d").replace("Đ", "d")
        return no_accent

    def extract_negated_scopes(self, text: str) -> list[tuple[int, int, str]]:
        """
        Xác định tất cả các đoạn (spans) bị phủ định trong văn bản.
        Trả về danh sách: [(start_idx, end_idx, negated_substring), ...]
        Phạm vi bắt đầu từ từ phủ định và kết thúc ở ranh giới mệnh đề tiếp theo.
        """
        scopes: list[tuple[int, int, str]] = []
        if not text:
            return scopes

        pseudo_spans = [(m.start(), m.end()) for m in self._pseudo_regex.finditer(text)]

        for match in self._all_negation_regex.finditer(text):
            neg_start = match.start()
            neg_word_end = match.end()

            # Bỏ qua nếu từ phủ định nằm trong một cụm bất định (pseudo-negation: "không rõ là", "không biết là")
            if any(p_start <= neg_start < p_end for p_start, p_end in pseudo_spans):
                continue

            # Tìm ranh giới kết thúc mệnh đề phủ định
            boundary_match = self.boundary_pattern.search(text, pos=neg_word_end)
            if boundary_match:
                scope_end = boundary_match.start()
            else:
                scope_end = len(text)

            scope_text = text[neg_start:scope_end].strip()
            scopes.append((neg_start, scope_end, scope_text))

        return scopes

    def is_phrase_negated(self, phrase: str, full_text: str) -> bool:
        """
        Kiểm tra xem một cụm từ / triệu chứng có nằm trong phạm vi phủ định hay không.
        Hỗ trợ so khớp cả tiếng Việt có dấu và không dấu.
        """
        if not phrase or not full_text:
            return False

        phrase_norm = self._normalize_ascii(phrase)
        text_norm = self._normalize_ascii(full_text)

        # Triệu chứng mang từ "không/chưa" là triệu chứng chỉ mất chức năng (VD: "không thở được", "không cử động được", "không nói được")
        # Bản thân từ "không" là một phần triệu chứng, không thể tự phủ định chính nó!
        if phrase_norm.startswith(("khong ", "chua ", "chang ", "cannot ", "unable to ", "can't ")):
            return False

        # 1. Kiểm tra trên text gốc
        scopes = self.extract_negated_scopes(full_text)
        for _, _, scope_str in scopes:
            scope_clean = self._normalize_ascii(scope_str)
            # Chống va chạm từ đồng âm không dấu: 'hỗ trợ' (ho tro), 'hỏi' (hoi) không phải là 'ho' (cough)
            if phrase_norm in {"ho", "bi ho"} and re.search(r"\bho\s+tro\b", scope_clean):
                continue
            if re.search(rf"\b{re.escape(phrase_norm)}\b", scope_clean, re.IGNORECASE):
                return True

        # 2. Kiểm tra trên text không dấu (chỉ áp dụng khi text gốc không có dấu tiếng Việt)
        has_accents = any(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", full_text))
        if not has_accents:
            norm_scopes = self.extract_negated_scopes(text_norm)
            for _, _, scope_str in norm_scopes:
                if phrase_norm in {"ho", "bi ho"} and re.search(r"\bho\s+tro\b", scope_str):
                    continue
                if re.search(rf"\b{re.escape(phrase_norm)}\b", scope_str, re.IGNORECASE):
                    return True

        return False

    def partition_symptoms(self, symptoms: list[str], full_text: str) -> dict[str, list[str]]:
        """
        Phân loại danh sách triệu chứng thành 2 tập:
        - positive: Người bệnh thực sự khẳng định có triệu chứng.
        - negative: Người bệnh phủ định (không có / đã hết).
        """
        positive: list[str] = []
        negative: list[str] = []

        for sym in symptoms:
            if self.is_phrase_negated(sym, full_text):
                negative.append(sym)
            else:
                positive.append(sym)

        return {"positive": positive, "negative": negative}

    def contains_any_positive(self, keywords: list[str], full_text: str) -> bool:
        """
        Kiểm tra xem có ít nhất MỘT từ khóa xuất hiện ở dạng khẳng định (positive) trong câu hay không.
        Nếu từ khóa xuất hiện nhưng nằm trọn trong vùng phủ định ('không đau ngực') -> trả về False.
        """
        text_norm = self._normalize_ascii(full_text)
        for kw in keywords:
            kw_norm = self._normalize_ascii(kw)
            if kw_norm in text_norm:
                if not self.is_phrase_negated(kw, full_text):
                    return True
        return False


_clinical_negation_service_instance: ClinicalNegationService | None = None


def get_clinical_negation_service() -> ClinicalNegationService:
    global _clinical_negation_service_instance
    if _clinical_negation_service_instance is None:
        _clinical_negation_service_instance = ClinicalNegationService()
    return _clinical_negation_service_instance
