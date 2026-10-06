# -*- coding: utf-8 -*-
import sys
import os
import io
import asyncio
sys.path.insert(0, os.path.abspath("."))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_facility_inquiry(query: str):
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

q = "Đau ở khớp ngón tay cái đấy, tôi đang phân vân chưa biết khám bệnh viện nào ở Hà nội nữa"
is_fac, reg = extract_facility_inquiry(q)
print("Query:", q)
print("is_asking_facility:", is_fac)
print("region:", reg)
