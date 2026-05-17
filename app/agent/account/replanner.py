from typing import Any

from app.agent.account.state import AccountAgentState


async def replanner(state: AccountAgentState) -> dict[str, Any]:
    if state.get("response"):
        return {"response": state["response"]}

    plan = state.get("plan", [])
    if plan:
        return {"plan": plan}

    return {"response": "信息不足，请补充商品详情文案或截图 OCR 文本后再评估。"}
