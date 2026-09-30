import asyncio
import sys

# Đảm bảo in tiếng Việt
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.medical_assistant.api.routes import chat_stream  # noqa: E402
from src.medical_assistant.domain.schemas import ChatRequest  # noqa: E402


async def main():
    print("=" * 60)
    print("📡 TEST STREAMING ENDPOINT (SERVER-SENT EVENTS - SSE)")
    print("=" * 60)

    req = ChatRequest(
        message="Tôi bị đau ngực dữ dội lan ra cánh tay trái",
        session_id="stream_test_session"
    )

    response = await chat_stream(req)

    print("Nhận stream từ Server:")
    async for chunk in response.body_iterator:
        print(chunk, end="", flush=True)

    print("\n" + "=" * 60)
    print("✅ TEST STREAM HOÀN TẤT THÀNH CÔNG!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
