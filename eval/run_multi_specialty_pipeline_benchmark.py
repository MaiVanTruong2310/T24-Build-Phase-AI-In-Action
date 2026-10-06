"""
Multi-Specialty Pipeline Benchmark Suite (20 Test Cases) - P-124
Khảo sát năng lực điều phối lâm sàng khi người bệnh có triệu chứng thuộc 2 chuyên khoa khác nhau:
- Đau ở cơ quan sinh tồn (Tim mạch, Hô hấp, Thần kinh) vs Đau dữ dội ở cơ quan ngoại vi (Khớp, Da, Răng)
- Vạch ra lộ trình (Pipeline) khám phân tầng: Bước 1 khám khoa nào trước, Bước 2 khám khoa nào sau
- Đánh giá sự hiểu biết về nguyên tắc:
  "Vị trí giải phẫu cơ quan sinh tồn luôn được ưu tiên hơn mức độ đau đơn thuần"
"""

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.medical_assistant.agent.graph import agent

MULTI_SPECIALTY_TEST_CASES = [
    {
        "id": "TC-MULTI-01",
        "category": "Tim mạch (ngực âm ỉ) vs Cơ xương khớp (khớp gối dữ dội)",
        "query": "Tôi bị đau nhức khớp gối dữ dội đi không nổi, kèm theo thỉnh thoảng hơi tức nghẹn ngực trái âm ỉ.",
        "expected_primary": "Trung tâm Tim mạch",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Vị trí ngực liên quan tim mạch sinh tồn luôn ưu tiên trước mức độ đau khớp gối",
    },
    {
        "id": "TC-MULTI-02",
        "category": "Thần kinh (nhìn mờ đau đầu) vs Tiêu hóa (đau bụng)",
        "query": "Đang bị đau bụng âm ỉ mấy ngày nay, mà tự nhiên 2 hôm nay đau đầu nửa đầu kèm mắt nhìn mờ nhòe.",
        "expected_primary": "Khoa Thần kinh",
        "expected_secondary": "Khoa Tiêu hóa - Gan mật",
        "rationale": "Thần kinh não bộ thị giác ưu tiên trước tiêu hóa",
    },
    {
        "id": "TC-MULTI-03",
        "category": "Hô hấp (hụt hơi thở rít) vs Da liễu (ngứa mề đay dữ dội)",
        "query": "Người nổi mẩn ngứa khắp người gãi trầy da rất khó chịu, với lại thấy khó thở hụt hơi thở rít khò khè.",
        "expected_primary": "Khoa Nội hô hấp",
        "expected_secondary": "Khoa Da liễu",
        "rationale": "Đường thở trao đổi khí ưu tiên trước tổn thương bề mặt da",
    },
    {
        "id": "TC-MULTI-04",
        "category": "Tiêu hóa (phân đen mùi tanh) vs Tai mũi họng (đau rát họng)",
        "query": "Cổ họng đau rát nuốt vướng 1 tuần, nhưng 2 hôm nay đi ngoài phân đen kịt mùi tanh nồng và đau tức thượng vị.",
        "expected_primary": "Khoa Tiêu hóa - Gan mật",
        "expected_secondary": "Khoa Tai - Mũi - Họng",
        "rationale": "Xuất huyết tiêu hóa nguy cơ sốc mất máu ưu tiên trước viêm họng",
    },
    {
        "id": "TC-MULTI-05",
        "category": "Tim mạch (loạn nhịp choáng) vs Cơ xương khớp (đau lưng dữ dội)",
        "query": "Đau thắt lưng dữ dội cúi xuống không được, nhưng thỉnh thoảng tim đập thình thịch loạn nhịp hồi hộp.",
        "expected_primary": "Trung tâm Tim mạch",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Rối loạn nhịp tim tuần hoàn ưu tiên trước đau thắt lưng cơ học",
    },
    {
        "id": "TC-MULTI-06",
        "category": "Thần kinh (yếu tay cầm đũa rơi) vs Tiêu hóa (trào ngược ợ chua)",
        "query": "Dạo này hay ợ chua nóng rát cổ họng, nhưng đáng lo hơn là tay phải tự nhiên thấy yếu cầm đũa hay rơi.",
        "expected_primary": "Khoa Thần kinh",
        "expected_secondary": "Khoa Tiêu hóa - Gan mật",
        "rationale": "Dấu hiệu thần kinh khu trú (yếu chi) nghi ngờ đột quỵ ưu tiên trước trào ngược dạ dày",
    },
    {
        "id": "TC-MULTI-07",
        "category": "Thận tiết niệu (tiểu máu buốt rắt) vs Cơ xương khớp (mỏi cổ vai gáy)",
        "query": "Mỏi cổ vai gáy do ngồi máy tính nhiều, đợt này tự nhiên đi tiểu thấy buốt rắt và nước tiểu đỏ như nước rửa thịt.",
        "expected_primary": "Khoa Thận - Tiết niệu",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Tiểu máu tổn thương hệ tiết niệu ưu tiên trước mỏi cơ vai gáy",
    },
    {
        "id": "TC-MULTI-08",
        "category": "Hô hấp (ho khạc ra vệt máu) vs Răng hàm mặt (đau nhức răng buốt óc)",
        "query": "Đau nhức răng hàm dưới buốt lên tận óc, đồng thời 3 ngày nay ho khạc ra vệt máu tươi kèm sốt nhẹ.",
        "expected_primary": "Khoa Nội hô hấp",
        "expected_secondary": "Khoa Răng - Hàm - Mặt",
        "rationale": "Ho ra máu tổn thương phế quản phổi ưu tiên trước đau nhức răng",
    },
    {
        "id": "TC-MULTI-09",
        "category": "Sản phụ khoa (trễ kinh đau bụng ra huyết) vs Cơ xương khớp (sưng đau gối)",
        "query": "Em bị đau khớp gối sau đá bóng, còn bạn gái trễ kinh 2 tuần hôm nay đau quặn bụng dưới ra huyết nâu.",
        "expected_primary": "Khoa Sản phụ khoa",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Nghi ngờ thai ngoài tử cung cấp tính ưu tiên khám khẩn trước chấn thương gối",
    },
    {
        "id": "TC-MULTI-10",
        "category": "Thần kinh (choáng ngất thoáng qua) vs Mắt (cộm ngứa đỏ)",
        "query": "Mắt bị cộm ngứa đỏ 1 bên, với lại tuần này bị choáng ngất thoáng qua 2 lần tỉnh dậy không nhớ gì.",
        "expected_primary": "Khoa Thần kinh",
        "expected_secondary": "Khoa Mắt",
        "rationale": "Cơn ngất mất ý thức thần kinh trung ương ưu tiên trước cộm ngứa mắt",
    },
    {
        "id": "TC-MULTI-11",
        "category": "Tim mạch (đè nặng ngực khi gắng sức) vs Tiêu hóa (táo bón)",
        "query": "Bị táo bón cả tuần nay đầy chướng bụng, nhưng khi leo cầu thang thì lồng ngực cứ đè nặng thắt lại phải dừng lại nghỉ.",
        "expected_primary": "Trung tâm Tim mạch",
        "expected_secondary": "Khoa Tiêu hóa - Gan mật",
        "rationale": "Đau thắt ngực khi gắng sức cảnh báo bệnh mạch vành ưu tiên trước táo bón",
    },
    {
        "id": "TC-MULTI-12",
        "category": "Tiêu hóa - Gan mật (đau hạ sườn phải sốt) vs Da liễu (mụn bọc viêm)",
        "query": "Mặt nổi nhiều mụn viêm đỏ, kèm đau tức liên tục vùng hạ sườn bên phải, ăn mỡ vào là buồn nôn sốt nhẹ.",
        "expected_primary": "Khoa Tiêu hóa - Gan mật",
        "expected_secondary": "Khoa Da liễu",
        "rationale": "Viêm túi mật/gan nội tạng ưu tiên trước mụn viêm ngoài da",
    },
    {
        "id": "TC-MULTI-13",
        "category": "Nội tiết (sút cân khát nước tiểu đêm) vs Cơ xương khớp (đau gót chân)",
        "query": "Đau thọt gót chân khi bước xuống giường buổi sáng, dạo này người sút 4kg, ăn nhiều mà hay khát nước đi tiểu đêm 4-5 lần.",
        "expected_primary": "Khoa Nội tiết - Đái tháo đường",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Rối loạn chuyển hóa đái tháo đường ưu tiên trước viêm cân gan chân",
    },
    {
        "id": "TC-MULTI-14",
        "category": "Thần kinh / Tiền đình (nhà cửa quay cuồng nôn) vs Tiêu hóa (đầy bụng ợ hơi)",
        "query": "Hay đầy bụng ợ hơi ăn không tiêu, nhưng sáng nay ngủ dậy mở mắt ra thấy nhà cửa quay cuồng nôn thốc nôn tháo ù một bên tai.",
        "expected_primary": "Khoa Thần kinh",
        "expected_secondary": "Khoa Tiêu hóa - Gan mật",
        "rationale": "Hội chứng tiền đình cấp tính ưu tiên trước rối loạn tiêu hóa nhẹ",
    },
    {
        "id": "TC-MULTI-15",
        "category": "Tim mạch (phù chân khó thở nằm kê cao) vs Tiết niệu (tiểu ít)",
        "query": "Hai mu bàn chân sưng phù ấn lõm cả tuần nay, đêm ngủ phải kê cao gối mới thở được, với lại đi tiểu ít hẳn.",
        "expected_primary": "Trung tâm Tim mạch",
        "expected_secondary": "Khoa Thận - Tiết niệu",
        "rationale": "Dấu hiệu suy tim ứ huyết sung huyết phổi ưu tiên trước tiết niệu",
    },
    {
        "id": "TC-MULTI-16",
        "category": "Hô hấp (thở khò khè rít) vs Cơ xương khớp (khớp ngón tay sưng cứng)",
        "query": "Khớp ngón tay sưng cứng vào buổi sáng, ngực thì thở khò khè nghe tiếng rít mỗi khi nằm xuống.",
        "expected_primary": "Khoa Nội hô hấp",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Co thắt phế quản đe dọa trao đổi khí ưu tiên trước viêm khớp ngón tay",
    },
    {
        "id": "TC-MULTI-17",
        "category": "Thần kinh (đau nửa mặt giật điện) vs Răng hàm mặt (đau nhức răng)",
        "query": "Đau nhức dữ dội nửa mặt giật như điện giật mỗi khi chạm vào má hoặc đánh răng, không rõ là đau răng hay dây thần kinh.",
        "expected_primary": "Khoa Thần kinh",
        "expected_secondary": "Khoa Răng - Hàm - Mặt",
        "rationale": "Nghi ngờ đau dây thần kinh số V ưu tiên trước khám răng",
    },
    {
        "id": "TC-MULTI-18",
        "category": "Tiêu hóa (nuốt nghẹn sút cân) vs Tai mũi họng (ngạt mũi chảy nước)",
        "query": "Hay ngạt mũi chảy nước mũi trong, nhưng độ này ăn cơm thấy nghẹn ở cổ họng phải uống nước mới trôi, sút 3kg.",
        "expected_primary": "Khoa Tiêu hóa - Gan mật",
        "expected_secondary": "Khoa Tai - Mũi - Họng",
        "rationale": "Nuốt nghẹn sút cân nghi ngờ bệnh lý thực quản ưu tiên trước viêm mũi dị ứng",
    },
    {
        "id": "TC-MULTI-19",
        "category": "Tim mạch (huyết áp kịch phát 170/100) vs Cơ xương khớp (ngón chân cái sưng gút)",
        "query": "Ngón chân cái sưng to đỏ rực đau buốt không chạm vào được, đo huyết áp ở nhà thấy vọt lên 170/100 kèm nặng đầu.",
        "expected_primary": "Trung tâm Tim mạch",
        "expected_secondary": "Khoa Chấn thương chỉnh hình & Cột sống",
        "rationale": "Cơn tăng huyết áp 170/100 nguy cơ xuất huyết não ưu tiên trước cơn gút cấp",
    },
    {
        "id": "TC-MULTI-20",
        "category": "Ung bướu (sờ thấy hạch nách cứng chắc) vs Da liễu (ngứa ngực)",
        "query": "Vùng da ngực hay bị ngứa đỏ, tình cờ sờ thấy một cục hạch cứng chắc ở nách trái không đau không di động.",
        "expected_primary": "Trung tâm Ung bướu",
        "expected_secondary": "Khoa Da liễu",
        "rationale": "Tầm soát hạch nách nghi ngờ u ác tính ưu tiên trước ngứa da bề mặt",
    },
]


async def run_pipeline_benchmark():
    print("=" * 85)
    print("BẮT ĐẦU CHẠY BENCHMARK ĐIỀU PHỐI ĐA KHOA (20 TEST CASES CHỒNG CHÉO) - P-124")
    print("=" * 85)

    results = []
    total_cost_usd = 0.0
    total_latency_ms = 0.0
    correct_pipeline_count = 0

    for case in MULTI_SPECIALTY_TEST_CASES:
        cid = case["id"]
        cat = case["category"]
        query = case["query"]
        exp_primary = case["expected_primary"]
        exp_secondary = case["expected_secondary"]

        t_start = time.perf_counter()
        thread_id = f"eval_pipe_{cid}_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            state = await agent.ainvoke({"query": query}, config=config)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000
        except Exception as e:
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000
            print(f"❌ [{cid}] Lỗi thực thi: {e}")
            continue

        total_latency_ms += t_elapsed_ms
        status = state.get("workflow_status")
        dept = state.get("suggested_department_name")
        resp_text = state.get("response", "")
        token_usage = state.get("token_usage", {})
        cost_usd = token_usage.get("estimated_cost_usd", 0.0)
        total_cost_usd += cost_usd

        # Kiểm tra xem Bước 1 có đúng khoa ưu tiên sinh tồn không
        has_primary = (dept == exp_primary) or (exp_primary.lower() in resp_text.lower())
        has_pipeline = "Lộ trình Khám Ưu tiên" in resp_text or "BƯỚC 1" in resp_text or "Bước 1" in resp_text
        has_secondary = exp_secondary.lower() in resp_text.lower()

        is_accurate = has_primary and has_pipeline and has_secondary
        if is_accurate:
            correct_pipeline_count += 1

        results.append({
            "id": cid,
            "category": cat,
            "query": query,
            "expected_step_1": exp_primary,
            "expected_step_2": exp_secondary,
            "actual_department": dept,
            "pipeline_generated": has_pipeline,
            "is_accurate": is_accurate,
            "latency_ms": round(t_elapsed_ms, 1),
            "status": status,
            "tokens": token_usage.get("total_tokens", 0),
            "cost_usd": cost_usd,
            "response_preview": resp_text[:140].replace("\n", " ") + "...",
            "full_response": resp_text,
        })

        status_icon = "✅" if is_accurate else ("⚠️" if has_primary else "❌")
        print(f"{status_icon} [{cid}] {cat}")
        print(f"   Query: \"{query}\"")
        print(f"   Lộ trình chuẩn: [Bước 1: {exp_primary}] -> [Bước 2: {exp_secondary}]")
        print(f"   Thực tế: Dept={dept} | Pipeline={has_pipeline} | Latency={t_elapsed_ms:.1f}ms")
        print(f"   Phản hồi: {resp_text[:120].strip()}...")
        print("-" * 85)

    avg_latency = total_latency_ms / len(results) if results else 0
    accuracy_rate = (correct_pipeline_count / len(results)) * 100 if results else 0

    print("\n" + "=" * 85)
    print("TỔNG KẾT BENCHMARK ĐA KHOA (20 CA CHỒNG CHÉO):")
    print(f"- Tổng số case hoàn thành: {len(results)}/20")
    print(f"- Tỷ lệ xác lập Pipeline chuẩn xác: {correct_pipeline_count}/{len(results)} ({accuracy_rate:.1f}%)")
    print(f"- Thời gian phản hồi trung bình: {avg_latency:.1f} ms")
    print(f"- Tổng chi phí token: ${total_cost_usd:.6f} USD (~{total_cost_usd * 25400:.2f} VNĐ)")
    print("=" * 85)

    # Save to JSON
    out_dir = ROOT_DIR / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "multi_specialty_pipeline_benchmark_20_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {
                    "cases": len(results),
                    "accurate_cases": correct_pipeline_count,
                    "accuracy_rate_pct": accuracy_rate,
                    "avg_latency_ms": avg_latency,
                    "total_cost_usd": total_cost_usd,
                },
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"✅ Đã lưu kết quả chi tiết tại: {out_path}")


if __name__ == "__main__":
    asyncio.run(run_pipeline_benchmark())
