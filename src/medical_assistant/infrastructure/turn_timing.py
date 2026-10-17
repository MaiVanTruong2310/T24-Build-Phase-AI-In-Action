"""Đo thời gian từng bước trong một lượt chat (node của graph, các bước ghi DB đầu lượt).

Dùng ContextVar giữ một dict dùng chung: các task con của LangGraph kế thừa cùng tham chiếu,
nên mọi node cộng dồn thời gian vào cùng một chỗ. Chỉ để chẩn đoán độ trễ, không ảnh hưởng nghiệp vụ.

Khi một bước chạy lâu hơn PROFILE_THRESHOLD_MS, bộ lấy mẫu stack (luồng nền, không dùng sys.setprofile
nên không xung đột với debugger/profiler khác) cho biết hàm/dòng nào đang chiếm thời gian. Mỗi mẫu được
tính trọng số bằng khoảng thời gian thật kể từ mẫu trước, nên một lời gọi C dài (vd. regex) vẫn bị gán
đúng vào dòng gọi nó. Kết quả ghi vào cùng dict với khóa "prof:<bước>:self|cum:<file:dòng(hàm)>".
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

turn_timings: ContextVar[dict[str, float] | None] = ContextVar("turn_timings", default=None)
# Kênh báo tiến trình cho /chat/stream: nhận tên giai đoạn ("node:analyze", "saving"...) ngay khi bắt đầu.
turn_progress: ContextVar[Callable[[str], None] | None] = ContextVar("turn_progress", default=None)


def notify_progress(stage: str) -> None:
    callback = turn_progress.get()
    if callback is None:
        return
    try:
        callback(stage)
    except Exception as exc:  # báo tiến trình không bao giờ được làm hỏng lượt chat
        logger.debug("turn progress callback failed: %s", exc)


PROFILE_ENABLED = os.getenv("PROFILE_SLOW_STEPS", "0") in {"1", "true", "True"}
PROFILE_THRESHOLD_MS = 1000.0
SAMPLE_INTERVAL_S = 0.004
_STDLIB_PREFIXES = tuple({sys.base_prefix, sys.prefix, sys.exec_prefix})


def record_ms(name: str, started: float) -> None:
    bucket = turn_timings.get()
    if bucket is not None:
        bucket[name] = round(bucket.get(name, 0.0) + (time.perf_counter() - started) * 1000, 1)


def _is_project_file(filename: str) -> bool:
    return (
        "site-packages" not in filename and not filename.startswith(_STDLIB_PREFIXES) and not filename.startswith("<")
    )


def _frame_label(frame: Any) -> str:
    code = frame.f_code
    return f"{os.path.basename(code.co_filename)}:{frame.f_lineno}({code.co_name})"


def _func_label(frame: Any) -> str:
    code = frame.f_code
    return f"{os.path.basename(code.co_filename)}:{code.co_firstlineno}({code.co_name})"


class _StackSampler:
    def __init__(self, target_ident: int) -> None:
        self._target = target_ident
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="turn-sampler", daemon=True)
        self.self_ms: dict[str, float] = {}
        self.cum_ms: dict[str, float] = {}

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def _run(self) -> None:
        last = time.perf_counter()
        while not self._stop.wait(SAMPLE_INTERVAL_S):
            now = time.perf_counter()
            weight_ms = (now - last) * 1000
            last = now
            frame = sys._current_frames().get(self._target)
            if frame is None:
                continue
            label = _frame_label(frame)
            seen: set[str] = set()
            caller_label = ""
            walker = frame
            while walker is not None:
                if _is_project_file(walker.f_code.co_filename):
                    if not caller_label and walker is not frame:
                        caller_label = _frame_label(walker)
                    func = _func_label(walker)
                    if func not in seen:
                        seen.add(func)
                        self.cum_ms[func] = self.cum_ms.get(func, 0.0) + weight_ms
                walker = walker.f_back
            # Nếu đang kẹt trong thư viện/stdlib (re, json...), ghi kèm dòng code của dự án đã gọi nó.
            if caller_label and not _is_project_file(frame.f_code.co_filename):
                label = f"{label} <- {caller_label}"
            self.self_ms[label] = self.self_ms.get(label, 0.0) + weight_ms


def _record_samples(step: str, sampler: _StackSampler) -> None:
    bucket = turn_timings.get()
    if bucket is None:
        return
    for label, ms in sorted(sampler.self_ms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
        bucket[f"prof:{step}:self:{label}"] = round(ms, 1)
    for label, ms in sorted(sampler.cum_ms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
        bucket[f"prof:{step}:cum:{label}"] = round(ms, 1)


@contextmanager
def profiled(step: str) -> Iterator[None]:
    """Đo bước `step`; nếu chậm hơn ngưỡng thì ghi thêm các hàm/dòng tốn thời gian nhất."""
    started = time.perf_counter()
    sampler: _StackSampler | None = None
    if PROFILE_ENABLED:
        try:
            sampler = _StackSampler(threading.get_ident())
            sampler.start()
        except Exception as exc:  # chẩn đoán không bao giờ được làm hỏng request
            logger.warning("turn sampler failed to start: %s", exc)
            sampler = None
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        if sampler is not None:
            try:
                sampler.stop()
                if elapsed_ms >= PROFILE_THRESHOLD_MS:
                    _record_samples(step, sampler)
            except Exception as exc:
                logger.warning("turn sampler failed to finish: %s", exc)
        record_ms(step, started)


def timed_node(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Bọc node của LangGraph để ghi thời gian chạy vào turn_timings["node:<name>"]."""
    if inspect.iscoroutinefunction(fn):

        @wraps(fn)
        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            notify_progress(f"node:{name}")
            with profiled(f"node:{name}"):
                return await fn(*args, **kwargs)

        return _async_wrapper

    @wraps(fn)
    def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        notify_progress(f"node:{name}")
        with profiled(f"node:{name}"):
            return fn(*args, **kwargs)

    return _sync_wrapper
