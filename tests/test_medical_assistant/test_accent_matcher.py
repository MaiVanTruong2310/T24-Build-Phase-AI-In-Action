"""Bộ biên dịch luật có dấu: dấu đã gõ phải đúng, dấu bị bỏ (một phần hoặc toàn bộ) vẫn khớp; phân độ tin cậy."""

import pytest

from src.medical_assistant.domain.accent_matcher import (
    AMBIGUOUS,
    CERTAIN,
    MISSING,
    char_class,
    confidence,
    prepare,
    rule,
)


def test_char_class_is_subset_of_marks():
    assert set(char_class("ự")) == {"ự", "ư", "ụ", "u"}
    assert set(char_class("ắ")) == {"ắ", "ă", "á", "a"}
    assert set(char_class("đ")) == {"đ", "d"}
    assert char_class("a") == "a"  # chữ không dấu chỉ khớp chính nó


@pytest.mark.parametrize(
    ("pat", "text"),
    [
        ("đau ngực", "đau ngực"),
        ("đau ngực", "dau nguc"),  # không dấu
        ("đau ngực", "đau ngưc"),  # thiếu thanh, còn dấu móc
        ("đau ngực", "dau ngực"),  # dấu nửa vời
        ("vôi bột", "voi bot"),
        ("tự tử", "tu tu"),
        ("lơ mơ", "lo mo"),
        ("co giật", "co giat"),
        ("rắn cắn", "ran can"),
    ],
)
def test_matches_when_user_omits_marks(pat, text):
    assert rule(pat).regex.search(prepare(text))


@pytest.mark.parametrize(
    ("pat", "text"),
    [
        ("vôi", "với"),
        ("mắt", "mất"),
        ("mắt", "mặt"),
        ("tự tử", "từ từ"),
        ("cầm", "cảm"),
        ("súng", "sưng"),
        ("rắn", "rạn"),
        ("lơ mơ", "lờ mờ"),
        ("bỏng", "bóng"),
        ("tột độ", "tối đó"),
        ("chảy dãi", "chạy dài"),
        ("ngã", "nga"),  # tên "Nga" (bác sĩ Nga) không phải "ngã"? xem test dưới
    ][:-1],
)
def test_wrong_typed_marks_do_not_match(pat, text):
    assert not rule(pat).regex.search(prepare(text))


def test_regex_syntax_preserved():
    r = rule(r"(?:hóa chất|vôi)[^.;]{0,40}\bmắt\b")
    assert r.regex.search(prepare("con tôi bị vôi bột bắn vào mắt"))
    assert not r.regex.search(prepare("Tôi bị ốm với ho khá nhiều cùng với việc cơ thể mệt mỏi và mất ngủ"))
    assert rule(r"(?<!không )đau").regex.search("đau")
    assert not rule(r"(?<!không )đau").regex.search("không đau")


@pytest.mark.parametrize(
    ("pat", "text", "level"),
    [
        ("vôi bột bắn vào mắt", "vôi bột bắn vào mắt", CERTAIN),
        ("đau ngực", "dau nguc", AMBIGUOUS),  # "dau" = đau/đầu/dầu (nhiều cách thêm dấu) → mơ hồ
        ("đau ngực dữ dội", "dau nguc du doi", MISSING),  # sàn: ≥ 3 từ của luật → không thể trùng ngẫu nhiên
        ("ngực", "nguc", MISSING),  # "nguc" chỉ có một dạng có dấu → chỉ thiếu dấu
        ("co giật", "co giat", MISSING),  # "co" luật vốn không dấu; "giat" tắc -t
        ("vôi bột", "voi bot", AMBIGUOUS),  # "voi" = con voi
        ("lơ mơ", "lo mo", AMBIGUOUS),
        ("hóa chất[^.;]{0,40}mắt", "hóa chất ban vao mắt", CERTAIN),  # chữ trong khoảng wildcard không tính
    ],
)
def test_confidence(pat, text, level):
    r = rule(pat)
    m = r.regex.search(prepare(text))
    assert m and confidence(r, m.group(0)) == level
