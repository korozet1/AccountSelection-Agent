import logging
from typing import Any

from app.agent.account.state import AccountAgentState
from app.tools.pxb7_crawler import is_pxb7_list_url

logger = logging.getLogger("planner")


async def planner(state: AccountAgentState) -> dict[str, Any]:
    has_url = bool(state.get("url"))
    is_list_url = is_pxb7_list_url(state.get("url"))

    if is_list_url:
        logger.info("列表页 URL，制定 3 步计划")
        return {
            "plan": [
                "抓取螃蟹平台列表页商品数据，自动滚动加载候选账号。",
                "对候选账号逐个提取售价、典藏、无双、珍品传说、传说、总皮肤等关键字段。",
                "LLM评估所有候选账号并生成最终报告。",
            ]
        }

    plan = []
    if has_url:
        plan.append("读取商品链接并提取页面文本；如果页面需要登录或反爬，则保留失败原因并继续使用手工文案。")
    plan.extend([
        "从商品详情文案中提取售价、典藏、无双、珍品传说、传说、总皮肤等关键字段。",
        "LLM评估账号并生成结构化评估报告。",
    ])
    logger.info("单账号评估，制定 %d 步计划", len(plan))
    return {"plan": plan}
