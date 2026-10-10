"""Kiểm thử tải cho endpoint chat: N người dùng ảo, mỗi người gửi K câu liên tiếp trong một phiên.

Cách chạy (backend phải đang chạy, nên là môi trường staging vì script gọi LLM thật và ghi dữ liệu thật vào DB):

    python scripts/load_test_chat.py --base-url http://localhost:8000 --users 100 --turns 10

Mỗi người dùng ảo là một khách (guest) riêng với cookie riêng, session_id riêng. Script in:
  - độ trễ người dùng thấy (p50/p90/p95/p99) và độ trễ backend tự đo (elapsed_ms),
  - tỉ lệ lỗi theo mã trạng thái, thông lượng (lượt/giây),
  - tổng token thật và chi phí ước tính (theo bảng giá backend đang dùng).
Gợi ý: chạy thử nhỏ trước (--users 5 --turns 3) rồi mới tăng lên.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field

import httpx

# Chuỗi hội thoại mẫu: chào, triệu chứng, trả lời câu hỏi thăm dò, hỏi bác sĩ/lịch.
SCRIPT = [
    "Chào bạn",
    "Tôi bị đau đầu và chóng mặt từ sáng nay",
    "Đau âm ỉ ở vùng trán, khoảng 3 ngày rồi",
    "Mức độ khoảng 5/10, không sốt",
    "Tôi muốn khám chuyên khoa nào thì phù hợp?",
    "Có bác sĩ nào còn lịch trống tuần này không?",
    "Tôi thấy đau thêm ở cổ gáy",
    "Không buồn nôn, không nhìn mờ",
    "Cho tôi xem các cơ sở gần nhất",
    "Cảm ơn bạn",
]


@dataclass
class Result:
    ok: bool
    status: int
    wall_ms: float
    backend_ms: float | None = None
    tokens: int = 0
    cost_usd: float = 0.0
    error: str = ""


@dataclass
class Stats:
    results: list[Result] = field(default_factory=list)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


async def virtual_user(
    index: int,
    args: argparse.Namespace,
    stats: Stats,
    gate: asyncio.Semaphore,
    start_at: float,
) -> None:
    await asyncio.sleep(max(0.0, start_at - time.monotonic()))
    session_id = f"load-{uuid.uuid4().hex[:16]}"
    headers = {"Origin": args.origin, "Content-Type": "application/json"}
    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout, headers=headers) as client:
        for turn in range(args.turns):
            message = SCRIPT[turn % len(SCRIPT)]
            started = time.perf_counter()
            result: Result
            try:
                async with gate:
                    response = await client.post(
                        "/api/v1/chat",
                        json={"message": message, "session_id": session_id, "request_id": str(uuid.uuid4())},
                    )
                wall_ms = (time.perf_counter() - started) * 1000
                if response.status_code == 200:
                    body = response.json()
                    usage = body.get("token_usage") or {}
                    result = Result(
                        ok=True,
                        status=200,
                        wall_ms=wall_ms,
                        backend_ms=body.get("elapsed_ms"),
                        tokens=int(usage.get("total_tokens") or 0),
                        cost_usd=float(usage.get("estimated_cost_usd") or 0.0),
                    )
                else:
                    result = Result(ok=False, status=response.status_code, wall_ms=wall_ms, error=response.text[:120])
            except Exception as exc:  # timeout, kết nối bị từ chối...
                wall_ms = (time.perf_counter() - started) * 1000
                result = Result(ok=False, status=0, wall_ms=wall_ms, error=f"{type(exc).__name__}: {exc}"[:120])
            stats.results.append(result)
            if turn < args.turns - 1:
                await asyncio.sleep(random.uniform(args.think_min, args.think_max))


def report(stats: Stats, elapsed_s: float, args: argparse.Namespace) -> None:
    results = stats.results
    ok = [r for r in results if r.ok]
    walls = [r.wall_ms for r in ok]
    backends = [r.backend_ms for r in ok if r.backend_ms]
    print("\n===== KẾT QUẢ KIỂM THỬ TẢI =====")
    print(f"Người dùng ảo: {args.users} | Số câu/người: {args.turns} | Tổng lượt gửi: {len(results)}")
    print(f"Thời gian chạy: {elapsed_s:.1f}s | Thông lượng: {len(results) / elapsed_s:.2f} lượt/giây")
    print(f"Thành công: {len(ok)} ({100 * len(ok) / max(1, len(results)):.1f}%) | Lỗi: {len(results) - len(ok)}")
    codes = Counter(r.status for r in results)
    print("Mã trạng thái:", dict(sorted(codes.items())))
    if walls:
        print(
            "Độ trễ người dùng thấy (ms): "
            f"p50={percentile(walls, 50):.0f} p90={percentile(walls, 90):.0f} "
            f"p95={percentile(walls, 95):.0f} p99={percentile(walls, 99):.0f} max={max(walls):.0f}"
        )
    if backends:
        print(
            "Độ trễ backend tự đo (ms):   "
            f"p50={statistics.median(backends):.0f} p95={percentile(backends, 95):.0f} max={max(backends):.0f}"
        )
    total_tokens = sum(r.tokens for r in ok)
    total_cost = sum(r.cost_usd for r in ok)
    llm_turns = sum(1 for r in ok if r.tokens > 0)
    print(f"Token thật: {total_tokens:,} (trung bình {total_tokens / max(1, llm_turns):.0f}/lượt có gọi LLM)")
    print(f"Chi phí ước tính: ${total_cost:.4f} (~${total_cost / max(1, len(ok)):.5f}/lượt)")
    errors = Counter(r.error for r in results if not r.ok)
    if errors:
        print("Lỗi phổ biến:")
        for message, count in errors.most_common(5):
            print(f"  {count}x {message}")
    print("\nNgưỡng gợi ý: p95 < 8000ms và lỗi < 1% khi tải ổn định; nếu p95 tăng vọt theo số người thì có nút thắt.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--origin", default="http://localhost:3000", help="Header Origin (phải nằm trong CORS_ORIGINS)")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--ramp", type=float, default=30.0, help="Giây để các người dùng vào dần (0 = cùng lúc)")
    parser.add_argument("--think-min", type=float, default=3.0, help="Giây nghỉ tối thiểu giữa 2 câu của một người")
    parser.add_argument("--think-max", type=float, default=10.0)
    parser.add_argument("--max-inflight", type=int, default=200, help="Trần số request đồng thời phía client")
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    stats = Stats()
    gate = asyncio.Semaphore(args.max_inflight)
    now = time.monotonic()
    started = time.perf_counter()
    tasks = [
        asyncio.create_task(
            virtual_user(i, args, stats, gate, now + (args.ramp * i / max(1, args.users) if args.ramp else 0))
        )
        for i in range(args.users)
    ]
    await asyncio.gather(*tasks)
    report(stats, time.perf_counter() - started, args)


if __name__ == "__main__":
    asyncio.run(main())
