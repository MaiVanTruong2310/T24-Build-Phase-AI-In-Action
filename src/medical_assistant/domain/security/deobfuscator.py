"""
Pre-Ingestion De-obfuscation & Anti-Evasion Engine.
Normalizes incoming text and decodes obfuscated attack vectors:
- Zero-width and invisible steganographic characters
- Unicode homoglyph confusables (Cyrillic/Greek -> Latin)
- Morse code
- Binary ASCII streams
- Hexadecimal strings
- Base64 / Base32 encodings
- Leetspeak & character substitution
- Token-splitting (spaced-out characters)
- Recursive unpacking (up to depth 2)
"""

import base64
import codecs
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import unquote

# Bảng mã Morse Quốc Tế chuẩn
MORSE_CODE_DICT = {
    ".-": "a", "-...": "b", "-.-.": "c", "-..": "d", ".": "e",
    "..-.": "f", "--.": "g", "....": "h", "..": "i", ".---": "j",
    "-.-": "k", ".-..": "l", "--": "m", "-.": "n", "---": "o",
    ".--.": "p", "--.-": "q", ".-.": "r", "...": "s", "-": "t",
    "..-": "u", "...-": "v", ".--": "w", "-..-": "x", "-.--": "y",
    "--..": "z", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
    ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9",
    "-----": "0", ".-.-.-": ".", "--..--": ",", "..--..": "?",
    "-.-.--": "!", "-....-": "-", "-..-.": "/", ".--.-.": "@",
}

# Ký tự tàng hình, Zero-width và directional override
INVISIBLE_CHARS = {
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u200e",  # Left-to-right mark
    "\u200f",  # Right-to-left mark
    "\u202a",  # Left-to-right embedding
    "\u202b",  # Right-to-left embedding
    "\u202c",  # Pop directional formatting
    "\u202d",  # Left-to-right override
    "\u202e",  # Right-to-left override
    "\u2060",  # Word joiner
    "\ufeff",  # Zero-width no-break space / BOM
    "\u00ad",  # Soft hyphen
}

# Unicode Homoglyphs phổ biến (Cyrillic, Greek, Math monospace sang Latin)
HOMOGLYPH_MAP = {
    "а": "a", "А": "A", "с": "c", "С": "C", "е": "e", "Е": "E",
    "о": "o", "О": "O", "р": "p", "Р": "P", "х": "x", "Х": "X",
    "у": "y", "У": "Y", "і": "i", "І": "I", "ј": "j", "Ј": "J",
    "ѕ": "s", "Ѕ": "S", "ԁ": "d", "Ԃ": "D", "ԛ": "q", "Ԛ": "Q",
    "ԝ": "w", "Ԝ": "W", "п": "n", "т": "t", "в": "b", "В": "B",
    "м": "m", "М": "M", "н": "h", "Н": "H", "к": "k", "К": "K",
    # Greek
    "α": "a", "Α": "A", "β": "b", "Β": "B", "γ": "y", "ε": "e",
    "Ε": "E", "η": "n", "Η": "H", "ι": "i", "Ι": "I", "κ": "k",
    "Κ": "K", "ν": "v", "Ν": "N", "ο": "o", "Ο": "O", "ρ": "p",
    "Ρ": "P", "τ": "t", "Τ": "T", "χ": "x", "Χ": "X",
}

# Leetspeak mappings
LEET_MAP = {
    "0": "o",
    "1": "i",
    "!": "i",
    "|": "i",
    "3": "e",
    "4": "a",
    "@": "a",
    "5": "s",
    "$": "s",
    "7": "t",
    "+": "t",
    "8": "b",
    "9": "g",
}


@dataclass
class DeobfuscationResult:
    original_text: str
    cleaned_text: str
    decoded_variants: set[str] = field(default_factory=set)
    detected_encodings: list[str] = field(default_factory=list)

    @property
    def all_text_representations(self) -> list[str]:
        """Tất cả các biến thể text có thể dùng để quét an toàn (từ gốc đến giải mã)."""
        res = [self.original_text, self.cleaned_text]
        for v in self.decoded_variants:
            if v not in res:
                res.append(v)
        return res


class Deobfuscator:
    MAX_INPUT_LENGTH = 12000
    MAX_DECODED_LENGTH = 6000
    MAX_CANDIDATES_PER_FORMAT = 12

    def __init__(self):
        # Regex kiểm tra chuỗi Morse: tập hợp ., -, _, /, space, ít nhất 3 ký tự
        self._morse_token_pattern = re.compile(r"^[\.\-\_/·\s]{3,}$")
        # Regex kiểm tra chuỗi nhị phân (từng byte 7-8 bit phân tách bởi dấu cách hoặc liền)
        self._binary_pattern = re.compile(r"\b([01]{7,8}(?:\s+[01]{7,8})+)\b")
        # Regex kiểm tra chuỗi Hex (\x61, 0x61, 48 65 6c 6c 6f)
        self._hex_pattern_prefixed = re.compile(r"(?:\\x|0x)([0-9a-fA-F]{2})")
        self._hex_pattern_spaced = re.compile(r"\b([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2}){2,})\b")
        # Regex Base64 pattern (chuỗi dài tối thiểu 8 ký tự, có thể có padding =)
        # Lookarounds are intentional: a trailing '=' is not a word character,
        # therefore \b used to miss padded Base64 embedded inside a sentence.
        self._b64_pattern = re.compile(
            r"(?<![A-Za-z0-9+/])(?:[A-Za-z0-9+/]{4}){3,}"
            r"(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?(?![A-Za-z0-9+/=])"
        )
        self._unicode_escape_pattern = re.compile(r"(?:\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}){2,}")
        self._percent_encoded_pattern = re.compile(r"%[0-9a-fA-F]{2}")

    def remove_invisible_chars(self, text: str) -> str:
        """Loại bỏ ký tự tàng hình và zero-width."""
        if not text:
            return ""
        return "".join(c for c in text if c not in INVISIBLE_CHARS)

    def normalize_homoglyphs(self, text: str) -> str:
        """Quy chuẩn các ký tự giả mạo Homoglyph (Cyrillic, Greek, Fullwidth) về Latin."""
        if not text:
            return ""
        # Chuẩn hóa NFKC trước để convert fullwidth
        normalized = unicodedata.normalize("NFKC", text)
        result = []
        for ch in normalized:
            result.append(HOMOGLYPH_MAP.get(ch, ch))
        return "".join(result)

    def decode_morse(self, text: str) -> str | None:
        """Giải mã chuỗi ký tự Morse nếu có."""
        cleaned = text.strip().replace("·", ".").replace("_", "-")
        if not self._morse_token_pattern.match(cleaned):
            return None

        # Chia theo từ (phân tách bởi / hoặc 3+ spaces)
        words = re.split(r"\s*/\s*|\s{3,}", cleaned)
        decoded_words = []
        has_valid_char = False

        for word in words:
            letters = word.strip().split()
            decoded_letters = []
            for letter in letters:
                if letter in MORSE_CODE_DICT:
                    decoded_letters.append(MORSE_CODE_DICT[letter])
                    has_valid_char = True
                else:
                    # Ký tự morse không hợp lệ
                    decoded_letters.append("?")
            if decoded_letters:
                decoded_words.append("".join(decoded_letters))

        if has_valid_char and decoded_words:
            res = " ".join(decoded_words).strip()
            # Chỉ trả về nếu kết quả có ý nghĩa (> 1 ký tự và không toàn ?)
            if len(res.replace("?", "")) >= 2:
                return res
        return None

    def decode_binary(self, text: str) -> str | None:
        """Giải mã nhị phân sang ASCII / UTF-8."""
        matches = self._binary_pattern.findall(text)
        decoded_segments = []
        for match in matches:
            bytes_list = []
            valid = True
            for chunk in match.split():
                try:
                    val = int(chunk, 2)
                    if 32 <= val <= 126 or val in (9, 10, 13) or val >= 128:
                        bytes_list.append(val)
                    else:
                        valid = False
                        break
                except ValueError:
                    valid = False
                    break
            if valid and bytes_list:
                try:
                    decoded_str = bytes(bytes_list).decode("utf-8", errors="ignore")
                    if len(decoded_str.strip()) >= 2:
                        decoded_segments.append(decoded_str)
                except Exception:
                    pass

        if decoded_segments:
            return " ".join(decoded_segments)
        return None

    def decode_hex(self, text: str) -> str | None:
        """Giải mã Hexadecimal sang ASCII / UTF-8."""
        # 1. Thử hex có tiền tố \x hoặc 0x
        prefixed_matches = self._hex_pattern_prefixed.findall(text)
        if len(prefixed_matches) >= 3:
            try:
                byte_vals = [int(h, 16) for h in prefixed_matches]
                decoded_str = bytes(byte_vals).decode("utf-8", errors="ignore")
                if len(decoded_str.strip()) >= 2 and any(c.isalnum() for c in decoded_str):
                    return decoded_str
            except Exception:
                pass

        # 2. Thử hex phân cách bằng khoảng trắng (ví dụ: 6b 65 20 64 6f 6e)
        spaced_matches = self._hex_pattern_spaced.findall(text)
        for match in spaced_matches:
            try:
                hex_tokens = match.split()
                byte_vals = [int(h, 16) for h in hex_tokens]
                decoded_str = bytes(byte_vals).decode("utf-8", errors="ignore")
                if len(decoded_str.strip()) >= 2 and any(c.isalnum() for c in decoded_str):
                    return decoded_str
            except Exception:
                pass

        # 3. Thử chuỗi hex liền không khoảng trắng có độ dài chẵn và toàn bộ là hex
        clean_text = text.strip()
        if (
            len(clean_text) >= 6
            and len(clean_text) % 2 == 0
            and re.fullmatch(r"[0-9a-fA-F]+", clean_text)
            # Tránh nhầm lẫn với mã slot UUID 8 ký tự của hệ thống P-124
            and not (len(clean_text) == 8 and re.match(r"[0-9a-fA-F]{8}$", clean_text))
        ):
            try:
                byte_vals = bytes.fromhex(clean_text)
                decoded_str = byte_vals.decode("utf-8", errors="ignore")
                # Kiểm tra xem có chứa ký tự in được và có nghĩa không
                if len(decoded_str.strip()) >= 3 and any(c.isalpha() for c in decoded_str):
                    return decoded_str
            except Exception:
                pass

        return None

    def decode_base64(self, text: str) -> str | None:
        """Giải mã Base64 an toàn nếu chuỗi là chuỗi mã hóa hợp lệ và ra ký tự in được."""
        # Bỏ qua nếu text quá ngắn
        if len(text.strip()) < 8:
            return None

        candidates = self._b64_pattern.findall(text)[: self.MAX_CANDIDATES_PER_FORMAT]
        # Nếu toàn bộ chuỗi có vẻ là base64
        clean_text = text.strip()
        if clean_text not in candidates and re.fullmatch(r"[A-Za-z0-9+/=]+", clean_text) and len(clean_text) % 4 == 0:
            candidates.append(clean_text)

        decoded_results = []
        for candidate in candidates:
            # Bỏ qua chuỗi toàn số hoặc không có padding/lowercase
            if len(candidate) < 8:
                continue
            try:
                # Add padding if needed
                padded = candidate + "=" * (-len(candidate) % 4)
                decoded_bytes = base64.b64decode(padded, validate=True)
                decoded_str = decoded_bytes.decode("utf-8")[: self.MAX_DECODED_LENGTH]
                # Chỉ nhận nếu kết quả chứa chữ cái và tỷ lệ ký tự in được > 85%
                printable_count = sum(1 for c in decoded_str if c.isprintable() or c in "\n\r\t")
                if (
                    len(decoded_str.strip()) >= 3
                    and printable_count / len(decoded_str) > 0.85
                    and any(c.isalpha() for c in decoded_str)
                ):
                    decoded_results.append(decoded_str)
            except Exception:
                continue

        if decoded_results:
            return " ".join(decoded_results)
        return None

    def decode_url_percent(self, text: str) -> str | None:
        """Decode percent-encoded fragments without treating ordinary '%' text as encoded."""
        if len(self._percent_encoded_pattern.findall(text)) < 2:
            return None
        try:
            decoded = unquote(text)[: self.MAX_DECODED_LENGTH]
            if decoded != text and len(decoded.strip()) >= 2 and any(c.isalnum() for c in decoded):
                return decoded
        except (UnicodeDecodeError, ValueError):
            pass
        return None

    def decode_unicode_escapes(self, text: str) -> str | None:
        """Decode explicit \\uXXXX/\\xXX fragments while leaving normal Unicode untouched."""
        if not self._unicode_escape_pattern.search(text):
            return None

        def _decode_match(match: re.Match) -> str:
            try:
                return codecs.decode(match.group(0), "unicode_escape")
            except (UnicodeDecodeError, ValueError):
                return match.group(0)

        decoded = self._unicode_escape_pattern.sub(_decode_match, text)[: self.MAX_DECODED_LENGTH]
        if decoded != text and len(decoded.strip()) >= 2 and any(c.isalnum() for c in decoded):
            return decoded
        return None

    def normalize_leetspeak(self, text: str) -> str:
        """Chuyển đổi Leetspeak sang chữ thường tương ứng."""
        res = []
        for char in text.lower():
            res.append(LEET_MAP.get(char, char))
        return "".join(res)

    def collapse_spaced_tokens(self, text: str) -> str:
        """
        Gộp các ký tự đơn lẻ bị cố tình ngắt bởi dấu cách để lách regex.
        Ví dụ: 'k e d o n t h u o c' -> 'kedon thuoc'.
        """
        # Nhận diện chuỗi gồm 3+ chữ cái đơn lẻ cách nhau đúng 1 dấu cách
        def _collapse(match):
            tokens = match.group(0).split()
            return "".join(tokens)

        pattern = r"\b[a-zA-Z0-9à-ỹÀ-Ỹ](?:\s+[a-zA-Z0-9à-ỹÀ-Ỹ]){2,}\b"
        return re.sub(pattern, _collapse, text)

    def process(self, raw_text: str, max_depth: int = 2) -> DeobfuscationResult:
        """
        Quy trình chuẩn hóa và bóc tách giải mã đệ quy (tối đa max_depth lần).
        Trả về DeobfuscationResult gồm text chuẩn hóa và tất cả các biến thể đã giải mã.
        """
        if not raw_text:
            return DeobfuscationResult(original_text="", cleaned_text="")

        # Bước 1: Loại bỏ ký tự ẩn & Homoglyphs
        # Bound CPU/memory cost before recursive decoding. The original text is
        # retained for auditing, while security analysis uses the bounded copy.
        bounded_text = raw_text[: self.MAX_INPUT_LENGTH]
        cleaned = self.remove_invisible_chars(bounded_text)
        cleaned = self.normalize_homoglyphs(cleaned)

        detected_techniques = []
        decoded_variants = set()

        if cleaned != raw_text:
            detected_techniques.append("INVISIBLE_OR_HOMOGLYPH")

        current_layer = [cleaned]

        # Bước 2: Giải mã đệ quy các chuẩn mã hóa
        for depth in range(max_depth):
            next_layer = []
            for item in current_layer:
                # 1. Thử Morse
                morse_dec = self.decode_morse(item)
                if morse_dec and morse_dec not in decoded_variants and morse_dec != item:
                    decoded_variants.add(morse_dec)
                    next_layer.append(morse_dec)
                    if "MORSE_CODE" not in detected_techniques:
                        detected_techniques.append("MORSE_CODE")

                # 2. Thử Binary
                bin_dec = self.decode_binary(item)
                if bin_dec and bin_dec not in decoded_variants and bin_dec != item:
                    decoded_variants.add(bin_dec)
                    next_layer.append(bin_dec)
                    if "BINARY_STREAM" not in detected_techniques:
                        detected_techniques.append("BINARY_STREAM")

                # 3. Thử Hex
                hex_dec = self.decode_hex(item)
                if hex_dec and hex_dec not in decoded_variants and hex_dec != item:
                    decoded_variants.add(hex_dec)
                    next_layer.append(hex_dec)
                    if "HEXADECIMAL" not in detected_techniques:
                        detected_techniques.append("HEXADECIMAL")

                # 4. Thử Base64
                b64_dec = self.decode_base64(item)
                if b64_dec and b64_dec not in decoded_variants and b64_dec != item:
                    decoded_variants.add(b64_dec)
                    next_layer.append(b64_dec)
                    if "BASE64" not in detected_techniques:
                        detected_techniques.append("BASE64")

                # 5. URL percent encoding (including encoded delimiters/spaces)
                url_dec = self.decode_url_percent(item)
                if url_dec and url_dec not in decoded_variants and url_dec != item:
                    decoded_variants.add(url_dec)
                    next_layer.append(url_dec)
                    if "URL_PERCENT_ENCODING" not in detected_techniques:
                        detected_techniques.append("URL_PERCENT_ENCODING")

                # 6. Literal Unicode/hex escape sequences
                unicode_dec = self.decode_unicode_escapes(item)
                if unicode_dec and unicode_dec not in decoded_variants and unicode_dec != item:
                    decoded_variants.add(unicode_dec)
                    next_layer.append(unicode_dec)
                    if "UNICODE_ESCAPE" not in detected_techniques:
                        detected_techniques.append("UNICODE_ESCAPE")

            if not next_layer:
                break
            current_layer = next_layer

        # Bước 3: Thêm các biến thể Leetspeak và Spaced-out
        all_variants_to_leet = [cleaned] + list(decoded_variants)
        for var in all_variants_to_leet:
            # Leetspeak
            leet_norm = self.normalize_leetspeak(var)
            if leet_norm != var.lower() and any(c in LEET_MAP for c in var.lower()):
                decoded_variants.add(leet_norm)
                if "LEETSPEAK" not in detected_techniques:
                    detected_techniques.append("LEETSPEAK")

            # Spaced tokens collapse
            collapsed = self.collapse_spaced_tokens(var)
            if collapsed != var:
                decoded_variants.add(collapsed)
                if "TOKEN_SPLITTING" not in detected_techniques:
                    detected_techniques.append("TOKEN_SPLITTING")

        return DeobfuscationResult(
            original_text=raw_text,
            cleaned_text=cleaned,
            decoded_variants=decoded_variants,
            detected_encodings=detected_techniques,
        )


_deobfuscator_instance: Deobfuscator | None = None


def get_deobfuscator() -> Deobfuscator:
    global _deobfuscator_instance
    if _deobfuscator_instance is None:
        _deobfuscator_instance = Deobfuscator()
    return _deobfuscator_instance
