from fastapi import APIRouter

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent."""
    result = await agent.ainvoke({"query": request.message})
    return ChatResponse(
        response=result.get("response", ""),
        analysis=result.get("analysis", ""),
    )


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
