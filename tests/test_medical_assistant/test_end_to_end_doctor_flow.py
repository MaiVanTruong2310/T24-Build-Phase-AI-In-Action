import asyncio

from src.medical_assistant.agent.graph import agent


async def run_end_to_end_test():
    print("=================================================================")
    print("TEST: Tích hợp hoàn chỉnh Triage -> Supabase Doctor Query -> Chat")
    print("=================================================================")

    thread_id = "test-session-doctor-query-001"
    config = {"configurable": {"thread_id": thread_id}}

    # Lượt 1: Bệnh nhân than đau đầu âm ỉ
    msg1 = "Tôi bị đau đầu âm ỉ vùng thái dương cả tuần nay rồi, hơi chóng mặt"
    print(f"\n[Bệnh nhân]: {msg1}")
    res1 = await agent.ainvoke({"query": msg1}, config=config)
    print(f"[Agent]:\n{res1.get('response')}")

    # Lượt 2: Bệnh nhân trả lời câu hỏi làm rõ và muốn xem bác sĩ
    msg2 = "Đau vừa phải thôi, không sốt, không buồn nôn, muốn đặt lịch khám luôn"
    print("\n-----------------------------------------------------------------")
    print(f"[Bệnh nhân]: {msg2}")
    res2 = await agent.ainvoke({"query": msg2}, config=config)
    print(f"[Agent]:\n{res2.get('response')}")

if __name__ == "__main__":
    asyncio.run(run_end_to_end_test())
