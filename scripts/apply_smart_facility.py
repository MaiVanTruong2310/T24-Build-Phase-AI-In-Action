# -*- coding: utf-8 -*-
with open('src/medical_assistant/agent/nodes/example_node.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add extract_facility_inquiry function near top
facility_fn = '''
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
    is_asking_facility = any(k in q for k in facility_keywords)
    return is_asking_facility, region
'''

if "def extract_facility_inquiry" not in text:
    old_anchor = "MAX_DETAILS_HISTORY = 4\n"
    assert old_anchor in text, "old_anchor not found"
    text = text.replace(old_anchor, old_anchor + facility_fn + "\n", 1)

# 2. Add smart fallback in analyze_node when intent_check is None
old_intent_check_block = '''    intent_check = guardrail.check_intent(query, current_department=current_dept, language=lang)
    boundary_intent = (intent_check or {}).get("intent")'''

new_intent_check_block = '''    intent_check = guardrail.check_intent(query, current_department=current_dept, language=lang)
    if not intent_check:
        fac_inquiry, fac_reg = extract_facility_inquiry(query)
        if fac_inquiry and fac_reg:
            intent_check = {
                "intent": "FACILITY_INFO",
                "matched_pattern": "smart_facility_extraction",
                "region_filter": fac_reg,
                "district_filter": None,
                "facility_name_query": None,
            }
    boundary_intent = (intent_check or {}).get("intent")'''

assert old_intent_check_block in text, "old_intent_check_block not found"
text = text.replace(old_intent_check_block, new_intent_check_block, 1)

# 3. Also trigger show_facility_info in v2_response action if smart facility intent matched
old_fac_action = '''        elif intent_name == "FACILITY_INFO":
            v2_response.proposed_action = "show_facility_info"'''
assert old_fac_action in text, "old_fac_action not found"
# it is already there, good!

# 4. Fix MsgPack ATSLevel serialization warning in serialize_candidate
old_ats_serialize = '"ats_level": candidate.ats_level,'
new_ats_serialize = '"ats_level": candidate.ats_level.value if hasattr(candidate.ats_level, "value") else candidate.ats_level,'
assert old_ats_serialize in text, "old_ats_serialize not found"
text = text.replace(old_ats_serialize, new_ats_serialize, 1)

with open('src/medical_assistant/agent/nodes/example_node.py', 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print('Updated example_node.py successfully!')
