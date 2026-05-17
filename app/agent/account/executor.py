import logging
from typing import Any

from app.agent.account.state import AccountAgentState
from app.tools.extractor import extract_account_metrics, metrics_from_dict
from app.tools.fetcher import fetch_listing_text
from app.tools.model_reviewer import (
    evaluate_batch_with_llm,
    evaluate_single_with_llm,
    is_model_configured,
)
from app.tools.pxb7_crawler import crawl_pxb7_list, is_pxb7_list_url
from app.tools.reporter import build_batch_markdown_report, build_markdown_report
from app.tools.scorer import evaluate_account

logger = logging.getLogger("executor")


async def executor(state: AccountAgentState) -> dict[str, Any]:
    plan = state.get("plan", [])
    if not plan:
        return {}

    task = plan[0]
    logger.info("执行步骤: %s", task[:60])
    url = state.get("url")
    detail_text = state.get("detail_text") or ""
    raw_text = state.get("raw_text") or detail_text
    warnings: list[str] = []
    step_result = ""
    update: dict[str, Any] = {"plan": plan[1:]}

    # --- Crawl list page ---
    if "抓取螃蟹平台列表页" in task:
        if not url:
            warnings.append("未提供列表页 URL。")
            step_result = "没有 URL，无法抓取列表页。"
        else:
            max_items = int(state.get("max_items") or 60)
            crawled = await crawl_pxb7_list(
                url,
                max_items=max_items,
                min_price=state.get("min_price"),
                max_price=state.get("max_price"),
            )
            if crawled.get("success"):
                listings = crawled.get("items", [])
                update["listings"] = listings
                total = crawled.get("total_collected", len(listings))
                budget = crawled.get("budget") or {}
                budget_text = ""
                if budget.get("min_price") is not None or budget.get("max_price") is not None:
                    budget_text = f"，预算 {budget.get('min_price') or 0}-{budget.get('max_price') or '不限'} 元"
                step_result = f"抓取成功，获得 {len(listings)} 个候选账号（页面实际收集 {total} 个{budget_text}）。"
            else:
                warnings.append(crawled.get("error", "列表页抓取失败"))
                update["listings"] = []
                step_result = f"列表页抓取失败：{crawled.get('error', '未知错误')}"

    # --- Fetch single URL ---
    elif "读取商品链接" in task:
        fetched = await fetch_listing_text(url) if url else None
        if fetched and fetched.text:
            raw_text = "\n".join(part for part in [detail_text, fetched.text] if part)
            step_result = f"链接读取成功，获得约 {len(fetched.text)} 个字符。"
        else:
            reason = fetched.error if fetched else "未提供链接"
            warnings.append(f"链接读取失败或无可用正文：{reason}")
            raw_text = detail_text
            step_result = f"链接读取未成功，原因：{reason}。后续使用已输入文案继续评估。"
        update["raw_text"] = raw_text

    # --- Extract fields from batch listings ---
    elif "对候选账号逐个提取" in task:
        listings = state.get("listings") or []
        enriched = []
        for item in listings:
            text = " ".join(
                [
                    str(item.get("title") or ""),
                    " ".join(item.get("attr_names") or []),
                    f"售价{item.get('price')}元" if item.get("price") is not None else "",
                ]
            )
            metrics = extract_account_metrics(text)
            if item.get("price") is not None:
                metrics.price = item["price"]
            for field in ("collections", "wushuang", "rare_legend"):
                if getattr(metrics, field) is None:
                    setattr(metrics, field, 0)
            enriched.append({**item, "metrics": metrics.model_dump()})
        update["listings"] = enriched
        if enriched:
            ranked = []
            for item in enriched:
                metrics = metrics_from_dict(item.get("metrics") or {})
                evaluation = evaluate_account(metrics, purpose=state.get("purpose", "共号/出租变现"))
                ranked.append({**item, "evaluation": evaluation.model_dump()})
            update["ranked_listings"] = ranked
            update["preview_report"] = build_batch_markdown_report(ranked)
        step_result = f"已对 {len(enriched)} 个候选账号完成字段提取。"

    # --- Extract fields from single account text ---
    elif "提取" in task and "售价" in task:
        metrics = extract_account_metrics(raw_text)
        update["metrics"] = metrics.model_dump()
        found_fields = [
            name
            for name, value in metrics.model_dump().items()
            if name != "notes" and value not in (None, "")
        ]
        step_result = "已提取字段：" + ("、".join(found_fields) if found_fields else "暂无明确字段")
        if metrics.notes:
            warnings.extend(metrics.notes)

    # --- LLM evaluation ---
    elif "LLM评估" in task:
        use_model = state.get("use_model", True)
        if not use_model:
            logger.info("LLM 评估已关闭，使用规则引擎")
            step_result, update = await _fallback_rule_evaluation(state, update, warnings)
        elif not is_model_configured():
            logger.warning("未配置模型 API key，退回规则评估")
            warnings.append("未配置模型 API key，退回规则评估。")
            step_result, update = await _fallback_rule_evaluation(state, update, warnings)
        else:
            try:
                listings = state.get("listings") or []
                if listings:
                    logger.info("开始 LLM 批量评估 %d 个账号...", len(listings))
                    progress_queue = state.get("progress_queue")

                    async def on_progress(event: dict[str, Any]) -> None:
                        if progress_queue is not None:
                            await progress_queue.put(event)

                    report = await evaluate_batch_with_llm(
                        listings,
                        purpose=state.get("purpose", "共号/出租变现"),
                        on_progress=on_progress,
                        custom_rules=state.get("custom_rules"),
                    )
                    step_result = f"LLM 已完成 {len(listings)} 个账号的评估并生成报告。"
                elif is_pxb7_list_url(url):
                    report = build_batch_markdown_report([])
                    step_result = "列表页没有可用候选账号，已生成空结果报告。"
                else:
                    logger.info("开始 LLM 单账号评估...")
                    metrics_dict = state.get("metrics") or {}
                    if not metrics_dict:
                        metrics = extract_account_metrics(raw_text)
                        metrics_dict = metrics.model_dump()
                    progress_queue = state.get("progress_queue")
                    if progress_queue is not None:
                        await progress_queue.put({
                            "type": "llm_batch_start",
                            "stage": "llm",
                            "message": "开始模型流式生成单账号报告。",
                            "batch": 1,
                            "total_batches": 1,
                        })

                    async def on_delta(delta: str) -> None:
                        if progress_queue is not None:
                            await progress_queue.put({
                                "type": "llm_delta",
                                "stage": "llm",
                                "batch": 1,
                                "total_batches": 1,
                                "delta": delta,
                            })

                    report = await evaluate_single_with_llm(
                        metrics_dict,
                        detail_text=raw_text,
                        purpose=state.get("purpose", "共号/出租变现"),
                        on_delta=on_delta,
                        custom_rules=state.get("custom_rules"),
                    )
                    if progress_queue is not None:
                        await progress_queue.put({
                            "type": "llm_batch_complete",
                            "stage": "llm",
                            "message": "模型流式生成单账号报告完成。",
                            "batch": 1,
                            "total_batches": 1,
                            "report": report,
                        })
                    step_result = "LLM 已完成账号评估并生成报告。"
                update["response"] = report
            except Exception as exc:
                logger.exception("LLM 评估失败，退回规则评估")
                warnings.append(f"LLM 评估失败，退回规则评估：{exc}")
                step_result, update = await _fallback_rule_evaluation(state, update, warnings)

    else:
        step_result = f"未识别的任务步骤：{task}"

    update["past_steps"] = [(task, step_result)]
    if warnings:
        update["warnings"] = warnings
    return update


async def _fallback_rule_evaluation(
    state: AccountAgentState,
    update: dict[str, Any],
    warnings: list[str],
) -> tuple[str, dict[str, Any]]:
    listings = state.get("listings") or []
    if listings:
        ranked = []
        for item in listings:
            metrics = metrics_from_dict(item.get("metrics") or {})
            evaluation = evaluate_account(metrics, purpose=state.get("purpose", "共号/出租变现"))
            ranked.append({**item, "evaluation": evaluation.model_dump()})
        ranked.sort(
            key=lambda item: (
                item.get("evaluation", {}).get("value_ratio") or 0,
                item.get("evaluation", {}).get("score") or 0,
            ),
            reverse=True,
        )
        report = build_batch_markdown_report(ranked)
        update["response"] = report
        return f"已用规则引擎完成 {len(ranked)} 个账号的批量评分。", update

    metrics_dict = state.get("metrics") or {}
    raw_text = state.get("raw_text") or state.get("detail_text") or ""
    metrics = metrics_from_dict(metrics_dict) if metrics_dict else extract_account_metrics(raw_text)
    evaluation = evaluate_account(metrics, purpose=state.get("purpose", "共号/出租变现"))
    report = build_markdown_report(evaluation.model_dump())
    update["response"] = report
    return (
        f"已用规则引擎完成评分，推荐级别 {evaluation.grade}，"
        f"估算合理价 {evaluation.fair_price:.0f} 元。",
        update,
    )
