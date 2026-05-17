import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.agent.account import AccountAgentState, executor, planner, replanner
from app.models.request import EvaluateRequest

NODE_PLANNER = "planner"
NODE_EXECUTOR = "executor"
NODE_REPLANNER = "replanner"


class AccountAgentService:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AccountAgentState)
        workflow.add_node(NODE_PLANNER, planner)
        workflow.add_node(NODE_EXECUTOR, executor)
        workflow.add_node(NODE_REPLANNER, replanner)
        workflow.set_entry_point(NODE_PLANNER)
        workflow.add_edge(NODE_PLANNER, NODE_EXECUTOR)
        workflow.add_edge(NODE_EXECUTOR, NODE_REPLANNER)
        workflow.add_conditional_edges(
            NODE_REPLANNER,
            self._should_continue,
            {NODE_EXECUTOR: NODE_EXECUTOR, END: END},
        )
        return workflow.compile()

    @staticmethod
    def _should_continue(state: AccountAgentState) -> str:
        if state.get("response"):
            return END
        if state.get("plan"):
            return NODE_EXECUTOR
        return END

    async def execute(self, request: EvaluateRequest) -> AsyncGenerator[dict[str, Any], None]:
        if not request.url and not request.detail_text:
            yield {
                "type": "error",
                "stage": "input",
                "message": "请至少输入商品链接或商品详情文案。",
            }
            return

        session_id = request.session_id or str(uuid4())
        progress_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        initial_state: AccountAgentState = {
            "input": request.combined_input(),
            "url": request.url,
            "detail_text": request.detail_text,
            "purpose": request.purpose,
            "max_items": request.max_items,
            "min_price": request.min_price,
            "max_price": request.max_price,
            "use_model": request.use_model,
            "custom_rules": request.custom_rules,
            "plan": [],
            "past_steps": [],
            "raw_text": request.detail_text or "",
            "metrics": {},
            "evaluation": {},
            "listings": [],
            "ranked_listings": [],
            "model_review": "",
            "preview_report": "",
            "response": "",
            "progress_queue": progress_queue,
            "warnings": [],
        }

        yield {
            "type": "status",
            "stage": "start",
            "message": f"开始评估，会话 {session_id}",
        }

        async def run_graph() -> None:
            final_response = ""
            final_state: dict[str, Any] = {}
            try:
                async for event in self.graph.astream(initial_state, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        final_state.update(node_output or {})
                        await progress_queue.put(self._format_event(node_name, node_output))
                        if node_output and node_output.get("response"):
                            final_response = node_output["response"]

                await progress_queue.put({
                    "type": "complete",
                    "stage": "complete",
                    "message": "评估完成",
                    "response": final_response or final_state.get("response", ""),
                })
            except Exception as exc:
                await progress_queue.put({
                    "type": "error",
                    "stage": "exception",
                    "message": f"评估失败：{exc}",
                })
            finally:
                await progress_queue.put(None)

        task = asyncio.create_task(run_graph())
        try:
            while True:
                event = await progress_queue.get()
                if event is None:
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()

    def _format_event(self, node_name: str, state: dict[str, Any] | None) -> dict[str, Any]:
        state = state or {}
        if node_name == NODE_PLANNER:
            plan = state.get("plan", [])
            return {
                "type": "plan",
                "stage": "planner",
                "message": f"Planner 已制定 {len(plan)} 个步骤",
                "plan": plan,
                "current_step": plan[0] if plan else "",
            }

        if node_name == NODE_EXECUTOR:
            past_steps = state.get("past_steps", [])
            step = past_steps[-1] if past_steps else ("Executor", "步骤执行中")
            if state.get("response"):
                return {
                    "type": "report",
                    "stage": "executor",
                    "message": step[1],
                    "current_step": step[0],
                    "report": state["response"],
                }
            if state.get("preview_report"):
                return {
                    "type": "report_preview",
                    "stage": "executor",
                    "message": step[1] + " 已先生成规则排序，模型复核继续运行。",
                    "current_step": step[0],
                    "report": state["preview_report"],
                    "remaining_steps": len(state.get("plan", [])),
                    "warnings": state.get("warnings", []),
                }
            return {
                "type": "step_complete",
                "stage": "executor",
                "message": step[1],
                "current_step": step[0],
                "remaining_steps": len(state.get("plan", [])),
                "warnings": state.get("warnings", []),
            }

        if node_name == NODE_REPLANNER:
            if state.get("response"):
                return {
                    "type": "report",
                    "stage": "replanner",
                    "message": "Replanner 判断信息足够，生成最终报告",
                    "report": state["response"],
                }
            plan = state.get("plan", [])
            return {
                "type": "status",
                "stage": "replanner",
                "message": f"Replanner 完成复核，继续下一步",
                "remaining_steps": len(plan),
                "current_step": plan[0] if plan else "",
            }

        return {
            "type": "status",
            "stage": node_name,
            "message": "节点执行完成",
        }


account_agent_service = AccountAgentService()
