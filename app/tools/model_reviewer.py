import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.llm import chat_completion, get_llm_config

logger = logging.getLogger("model_reviewer")

BASELINE = {
    "price": 1300,
    "collections": 3,
    "wushuang": 3,
    "rare_legend": 2,
    "legend": 30,
    "skins": 400,
}

MAX_PER_BATCH = 25
ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]

SKIN_QUALITY_POLICY = {
    "rule": "不要只看典藏/无双/珍品传说/传说数量；同时看 skin_quality_score、top_skins、weak_skins。",
    "score_meaning": "skin_quality_score 已按高口碑皮肤加分、老旧/争议/低价值皮肤扣分，可直接影响排序和估值解释。",
    "decision": "同等数量下，优先推荐命中 top_skins 多且 weak_skins 少的账号；弱款多的账号必须压价。",
}

SYSTEM_PROMPT_BATCH = """你是王者荣耀账号评估专家。根据给定的基准线（朋友的好号标准），评估所有候选账号。

## 基准线
- 价格：1300 元 | 典藏：3 | 无双：3 | 珍品传说：2 | 传说：30 | 总皮肤：~400

## 评估规则
1. **性价比**：合理价 ≈ 1300 × (加权得分 / 100)，最高建议买入价 = 合理价 × 0.92
   权重：典藏24% 无双18% 珍品传说12% 传说28% 皮肤18%，再叠加 skin_quality_score
2. **出租/共号适配度**：典藏+无双+珍品传说 ≥ 8 且传说 ≥ 28 且皮肤 ≥ 380 为"适合"；高价值皮肤 ≥ 5 且传说 ≥ 20 且皮肤 ≥ 300 为"勉强适合"；否则"不太适合"
3. **皮肤质量**：必须参考 skin_quality_score、top_skins、weak_skins；同等数量下优先推荐顶级皮肤多、弱款少的账号。
4. **推荐级别**：划算(估值/售价≥1.18) | 一般(0.98~1.18) | 偏贵(0.82~0.98) | 低价备选 | 避开

## 输出要求（严格遵守！）
输出中文 Markdown，结构如下：

### 排名表格
**必须包含全部 {total} 个账号，一个都不能省略！** 按估值/售价从高到低排序。
列：排名 | 推荐 | 售价 | 合理价 | 最高买入 | 估值/售价 | 质量分 | 典藏 | 无双 | 珍品传说 | 传说 | 皮肤 | 商品

### 重点分析
选择估值/售价最高的前 5 个和最差的 3 个做简要分析，每个不超过 3 行。

### 购买策略
简要的砍价策略和核验清单。

注意：
- 商品列格式：[商品编号](url)，不要只输出纯数字
- 合理价和最高买入价精确到整数
- 估值/售价精确到 2 位小数
- 不要省略任何账号！总数为 {total}，表格应有 {total} 行数据
- 不要编造字段，缺失字段留空或标"-"
"""

SYSTEM_PROMPT_SINGLE = """你是王者荣耀账号评估专家。根据给定的基准线（朋友的好号标准），评估这个账号。

## 基准线
- 价格：1300 元 | 典藏：3 | 无双：3 | 珍品传说：2 | 传说：30 | 总皮肤：~400

## 评估维度
1. **字段对比**：典藏、无双、珍品传说、传说、总皮肤与基准线的差距
2. **性价比**：合理价 ≈ 1300 × (加权得分 / 100)，最高建议买入价 = 合理价 × 0.92
   权重：典藏24% 无双18% 珍品传说12% 传说28% 皮肤18%，再叠加 skin_quality_score
3. **出租/共号适配度**：典藏+无双+珍品传说 ≥ 8 且传说 ≥ 28 且皮肤 ≥ 380 为"适合"；高价值皮肤 ≥ 5 且传说 ≥ 20 且皮肤 ≥ 300 为"勉强适合"；否则"不太适合"
4. **皮肤质量**：必须参考 skin_quality_score、top_skins、weak_skins；同等数量下优先推荐顶级皮肤多、弱款少的账号。
5. **风险**：皮肤厚度不足、稀有度缺口、价格虚高等

## 推荐级别
- **划算**：估值/售价 ≥ 1.18
- **一般**：0.98 ≤ 估值/售价 < 1.18
- **偏贵**：0.82 ≤ 估值/售价 < 0.98
- **低价备选**：出租不太适合但价格很便宜
- **避开**：明显不值

## 输出要求
输出中文 Markdown 报告，包含：核心字段对比表、皮肤质量命中、推荐级别和综合评分、估算合理价和最高建议买入价、出租/共号适配度判断、风险和核验点、购买建议。

注意：只基于提供的数据分析，不要编造缺失字段。"""


def is_model_configured() -> bool:
    return get_llm_config() is not None


def _build_candidates(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for idx, item in enumerate(listings, 1):
        metrics = item.get("metrics", {})
        candidates.append({
            "index": idx,
            "product_id": item.get("product_id", ""),
            "title": " ".join(str(item.get("title", "")).split())[:120],
            "price": metrics.get("price"),
            "url": item.get("url", ""),
            "collections": metrics.get("collections"),
            "wushuang": metrics.get("wushuang"),
            "rare_legend": metrics.get("rare_legend"),
            "legend": metrics.get("legend"),
            "skins": metrics.get("skins"),
            "heroes": metrics.get("heroes"),
            "rank": metrics.get("rank"),
            "skin_quality_score": metrics.get("skin_quality_score"),
            "top_skins": metrics.get("top_skins", []),
            "weak_skins": metrics.get("weak_skins", []),
        })
    return candidates


async def evaluate_batch_with_llm(
    listings: list[dict[str, Any]],
    purpose: str = "共号/出租变现",
    on_progress: ProgressCallback | None = None,
    custom_rules: dict[str, str] | None = None,
) -> str:
    candidates = _build_candidates(listings)
    total = len(candidates)

    if total <= MAX_PER_BATCH:
        batch_report = []
        if on_progress:
            await on_progress({
                "type": "llm_batch_start",
                "stage": "llm",
                "message": f"开始模型复核第 1/1 批，共 {total} 个账号。",
                "batch": 1,
                "total_batches": 1,
            })

        async def on_delta(delta: str) -> None:
            batch_report.append(delta)
            if on_progress:
                await on_progress({
                    "type": "llm_delta",
                    "stage": "llm",
                    "batch": 1,
                    "total_batches": 1,
                    "delta": delta,
                })

        report = await _call_llm_batch(candidates, purpose, total, on_delta=on_delta, custom_rules=custom_rules)
        if on_progress:
            await on_progress({
                "type": "llm_batch_complete",
                "stage": "llm",
                "message": "模型复核第 1/1 批完成。",
                "batch": 1,
                "total_batches": 1,
                "report": report,
            })
        return report

    # Split into batches
    total_batches = (total + MAX_PER_BATCH - 1) // MAX_PER_BATCH
    logger.info("共 %d 个账号，分 %d 批评估", total, total_batches)
    if on_progress:
        await on_progress({
            "type": "llm_batches_planned",
            "stage": "llm",
            "message": f"模型复核共 {total} 个账号，分 {total_batches} 批。",
            "total_candidates": total,
            "total_batches": total_batches,
        })
    all_reports = []
    for batch_idx in range(0, total, MAX_PER_BATCH):
        batch = candidates[batch_idx:batch_idx + MAX_PER_BATCH]
        batch_num = batch_idx // MAX_PER_BATCH + 1
        batch_report = []
        logger.info("评估第 %d/%d 批，%d 个账号...", batch_num, total_batches, len(batch))
        if on_progress:
            await on_progress({
                "type": "llm_batch_start",
                "stage": "llm",
                "message": f"开始模型复核第 {batch_num}/{total_batches} 批，{len(batch)} 个账号。",
                "batch": batch_num,
                "total_batches": total_batches,
            })

        async def on_delta(delta: str, current_batch: int = batch_num) -> None:
            batch_report.append(delta)
            if on_progress:
                await on_progress({
                    "type": "llm_delta",
                    "stage": "llm",
                    "batch": current_batch,
                    "total_batches": total_batches,
                    "delta": delta,
                })

        report = await _call_llm_batch(
            batch,
            purpose,
            len(batch),
            batch_label=f"第{batch_num}批",
            on_delta=on_delta,
            custom_rules=custom_rules,
        )
        all_reports.append(report)
        if on_progress:
            await on_progress({
                "type": "llm_batch_complete",
                "stage": "llm",
                "message": f"模型复核第 {batch_num}/{total_batches} 批完成。",
                "batch": batch_num,
                "total_batches": total_batches,
                "report": report,
            })

    # Combine reports
    combined = [
        f"# 螃蟹列表页筛选报告\n",
        f"共 {total} 个候选账号，分 {len(all_reports)} 批评估。\n",
    ]
    for i, report in enumerate(all_reports):
        # Strip the top-level heading from each batch report
        lines = report.split("\n")
        # Remove leading "# 螃蟹列表页筛选报告" or similar from batches
        filtered = [l for l in lines if not l.startswith("# 螃蟹列表页筛选报告")]
        combined.append(f"## 第 {i+1} 批\n")
        combined.append("\n".join(filtered))
        combined.append("\n")

    combined.append("## 说明\n")
    combined.append("- 规则评分负责可复现估值；LLM 负责分析和推荐。\n")
    combined.append("- 买前核验实名、找回包赔、截图一致性、卖家信用和平台保障。\n")
    return "\n".join(combined)


async def _call_llm_batch(
    candidates: list[dict[str, Any]],
    purpose: str,
    total: int,
    batch_label: str = "",
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    custom_rules: dict[str, str] | None = None,
) -> str:
    rules = custom_rules or {}
    prompt = SYSTEM_PROMPT_BATCH.replace("{total}", str(total))
    if rules.get("system_prompt"):
        prompt += "\n\n## 用户补充规则\n" + rules["system_prompt"]
    skin_policy = SKIN_QUALITY_POLICY
    if rules.get("skin_quality"):
        skin_policy = {**SKIN_QUALITY_POLICY, "user_rules": rules["skin_quality"]}
    baseline = BASELINE
    if rules.get("baseline"):
        try:
            parsed = json.loads(rules["baseline"])
            if isinstance(parsed, dict):
                baseline = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    label_text = f"（{batch_label}）" if batch_label else ""
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "purpose": purpose,
                    "baseline": baseline,
                    "skin_quality_policy": skin_policy,
                    "total_candidates": total,
                    "candidates": candidates,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]
    logger.info("调用 LLM 评估 %d 个账号%s", total, label_text)
    return await chat_completion(messages, temperature=0.3, on_delta=on_delta)


async def evaluate_single_with_llm(
    metrics: dict[str, Any],
    detail_text: str = "",
    purpose: str = "共号/出租变现",
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    custom_rules: dict[str, str] | None = None,
) -> str:
    rules = custom_rules or {}
    system_prompt = SYSTEM_PROMPT_SINGLE
    if rules.get("system_prompt"):
        system_prompt += "\n\n## 用户补充规则\n" + rules["system_prompt"]
    skin_policy = SKIN_QUALITY_POLICY
    if rules.get("skin_quality"):
        skin_policy = {**SKIN_QUALITY_POLICY, "user_rules": rules["skin_quality"]}
    baseline = BASELINE
    if rules.get("baseline"):
        try:
            parsed = json.loads(rules["baseline"])
            if isinstance(parsed, dict):
                baseline = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    user_content = {
        "purpose": purpose,
        "baseline": baseline,
        "account": {
            "price": metrics.get("price"),
            "collections": metrics.get("collections"),
            "wushuang": metrics.get("wushuang"),
            "rare_legend": metrics.get("rare_legend"),
            "legend": metrics.get("legend"),
            "skins": metrics.get("skins"),
            "heroes": metrics.get("heroes"),
            "rank": metrics.get("rank"),
            "skin_quality_score": metrics.get("skin_quality_score"),
            "top_skins": metrics.get("top_skins", []),
            "weak_skins": metrics.get("weak_skins", []),
        },
        "skin_quality_policy": skin_policy,
    }
    if detail_text:
        user_content["detail_text"] = detail_text[:2000]

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(user_content, ensure_ascii=False, indent=2),
        },
    ]
    return await chat_completion(messages, temperature=0.3, on_delta=on_delta)
