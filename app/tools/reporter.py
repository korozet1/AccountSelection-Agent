from typing import Any


def build_markdown_report(evaluation: dict[str, Any]) -> str:
    metrics = evaluation.get("metrics", {})
    rows = evaluation.get("comparisons", [])
    missing = evaluation.get("missing_fields", [])
    risks = evaluation.get("risks", [])

    lines = [
        "# 王者荣耀账号评估报告",
        "",
        f"**推荐级别：{evaluation.get('grade', '未知')}**",
        f"**综合评分：{evaluation.get('score', 0)} / 100+**",
        f"**估算合理价：{evaluation.get('fair_price', 0):.0f} 元**",
        f"**最高建议买入价：{evaluation.get('max_buy_price', 0):.0f} 元**",
    ]

    value_ratio = evaluation.get("value_ratio")
    lines.append(f"**估值/售价比：{value_ratio:.2f}**" if value_ratio is not None else "**估值/售价比：缺少售价**")

    lines.extend(["", "## 核心字段", "", "| 字段 | 实际 | 基准 | 差距 | 判断 |", "|---|---:|---:|---:|---|"])
    for row in rows:
        lines.append(
            f"| {row.get('name')} | {_display(row.get('actual'))} | {_display(row.get('baseline'))} | "
            f"{_display(row.get('delta'))} | {row.get('comment')} |"
        )

    if metrics.get("skin_quality_score") is not None:
        lines.extend(["", "## 皮肤质量", ""])
        lines.append(f"- 质量加减分：{_display(metrics.get('skin_quality_score'))}")
        if metrics.get("top_skins"):
            lines.append("- 高价值命中：" + "、".join(metrics.get("top_skins", [])[:8]))
        if metrics.get("weak_skins"):
            lines.append("- 低价值/争议命中：" + "、".join(metrics.get("weak_skins", [])[:6]))
        for note in metrics.get("skin_quality_notes", [])[:2]:
            lines.append(f"- {note}")

    lines.extend(["", "## 用途判断", "", evaluation.get("rental_fit", "信息不足"), "", "## 建议", "", evaluation.get("recommendation", "信息不足。")])

    if risks:
        lines.extend(["", "## 风险和核验点", ""])
        lines.extend([f"- {risk}" for risk in risks])
    if missing:
        lines.extend(["", "## 需要补充的信息", "", "、".join(missing)])

    extra = []
    if metrics.get("heroes") is not None:
        extra.append(f"英雄数：{metrics.get('heroes')}")
    if metrics.get("rank"):
        extra.append(f"段位：{metrics.get('rank')}")
    if extra:
        lines.extend(["", "## 其他识别信息", "", "；".join(extra)])
    return "\n".join(lines)


def build_batch_markdown_report(ranked_items: list[dict[str, Any]], model_review: str = "") -> str:
    if not ranked_items:
        return "# 螃蟹列表页筛选报告\n\n没有抓到可评估的账号。"

    lines = [
        "# 螃蟹列表页筛选报告",
        "",
        f"本次抓取并评估 {len(ranked_items)} 个候选账号。规则排序会先看共号/出租适配度，再看估值/售价比。",
        "",
        "| 排名 | 推荐 | 售价 | 合理价 | 最高买入 | 估值/售价 | 质量分 | 典藏 | 无双 | 珍品传说 | 传说 | 皮肤 | 商品 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    display_items = sorted(ranked_items, key=_ranking_key, reverse=True)
    for rank, item in enumerate(display_items, 1):
        evaluation = item.get("evaluation", {})
        metrics = evaluation.get("metrics", item.get("metrics", {}))
        title = _compact(item.get("title") or "", 42)
        link = item.get("url") or ""
        product = f"[{title}]({link})" if link else title
        lines.append(
            "| {rank} | {grade} | {price} | {fair} | {max_buy} | {ratio} | {quality} | {collections} | {wushuang} | {rare} | {legend} | {skins} | {product} |".format(
                rank=rank,
                grade=evaluation.get("grade", "-"),
                price=_display(metrics.get("price")),
                fair=_display(evaluation.get("fair_price")),
                max_buy=_display(evaluation.get("max_buy_price")),
                ratio=_display(evaluation.get("value_ratio")),
                quality=_display(metrics.get("skin_quality_score")),
                collections=_display(metrics.get("collections")),
                wushuang=_display(metrics.get("wushuang")),
                rare=_display(metrics.get("rare_legend")),
                legend=_display(metrics.get("legend")),
                skins=_display(metrics.get("skins")),
                product=product,
            )
        )

    best = display_items[0]
    best_eval = best.get("evaluation", {})
    best_fit = best_eval.get("rental_fit", "")
    best_grade = best_eval.get("grade", "")
    if best_grade in {"划算", "一般"} and ("适合共号/出租" in best_fit or "勉强适合" in best_fit):
        best_title = "规则首选账号"
    elif "勉强适合" in best_fit:
        best_title = "规则最高适配账号（需要压价）"
    else:
        best_title = "规则最高分账号（不等于出租首选）"
    lines.extend(
        [
            "",
            f"## {best_title}",
            "",
            f"- 推荐级别：{best_eval.get('grade', '-')}",
            f"- 售价：{_display(best_eval.get('metrics', {}).get('price'))} 元",
            f"- 最高建议买入价：{_display(best_eval.get('max_buy_price'))} 元",
            f"- 皮肤质量分：{_display(best_eval.get('metrics', {}).get('skin_quality_score'))}",
            f"- 用途判断：{best_eval.get('rental_fit', '-')}",
            f"- 商品链接：{best.get('url') or '-'}",
        ]
    )
    best_metrics = best_eval.get("metrics", {})
    if best_metrics.get("top_skins"):
        lines.append(f"- 高价值命中：{'、'.join(best_metrics.get('top_skins', [])[:5])}")
    if best_grade in {"避开", "偏贵", "信息不足"}:
        lines.append("- 结论：当前候选池没有明确的买入首选，这个账号只是规则排序下最值得进一步核验的候选。")

    if model_review:
        lines.extend(["", "## 模型复核", "", model_review])

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 规则评分负责可复现估值；模型复核负责解释、排除矛盾和给购买策略。",
            "- 买前还要核验实名、找回包赔、截图一致性、卖家信用和平台保障。",
        ]
    )
    return "\n".join(lines)


def _ranking_key(item: dict[str, Any]) -> tuple[float, float, float, float, float]:
    evaluation = item.get("evaluation", {})
    metrics = evaluation.get("metrics", item.get("metrics", {}))
    rental_fit = evaluation.get("rental_fit", "")
    grade = evaluation.get("grade", "")
    viable_bonus = 1.0 if grade in {"划算", "一般", "低价备选"} else 0.0
    fit_bonus = 2.0 if "适合共号/出租" in rental_fit else 1.0 if "勉强适合" in rental_fit else 0.0
    return (
        viable_bonus,
        fit_bonus,
        float(evaluation.get("value_ratio") or 0),
        float(metrics.get("skin_quality_score") or 0),
        float(metrics.get("skins") or 0),
    )


def _display(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.0f}" if value.is_integer() else f"{value:.1f}"
    return str(value)


def _compact(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."
