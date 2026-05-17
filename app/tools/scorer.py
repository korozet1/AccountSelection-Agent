from app.models.account import AccountMetrics, Baseline, EvaluationResult, FieldComparison


WEIGHTS = {
    "collections": 24.0,
    "wushuang": 18.0,
    "rare_legend": 12.0,
    "legend": 28.0,
    "skins": 18.0,
}

FIELD_LABELS = {
    "collections": "典藏",
    "wushuang": "无双",
    "rare_legend": "珍品传说",
    "legend": "传说",
    "skins": "总皮肤",
}


def evaluate_account(
    metrics: AccountMetrics,
    purpose: str = "共号/出租变现",
    baseline: Baseline | None = None,
) -> EvaluationResult:
    baseline = baseline or Baseline()
    comparisons = _build_comparisons(metrics, baseline)
    score = _score(metrics, baseline)
    fair_price = _fair_price(metrics, baseline, score)
    max_buy_price = round(fair_price * 0.92, 2)
    value_ratio = round(fair_price / metrics.price, 3) if metrics.price else None
    rental_fit = _rental_fit(metrics, purpose)
    risks = _risks(metrics, baseline, value_ratio, rental_fit)
    missing_fields = _missing_fields(metrics)
    grade = _grade(value_ratio, rental_fit, missing_fields)
    recommendation = _recommendation(grade, rental_fit, missing_fields)

    return EvaluationResult(
        metrics=metrics,
        baseline=baseline,
        comparisons=comparisons,
        fair_price=round(fair_price, 2),
        max_buy_price=max_buy_price,
        value_ratio=value_ratio,
        score=round(score, 1),
        grade=grade,
        recommendation=recommendation,
        rental_fit=rental_fit,
        risks=risks,
        missing_fields=missing_fields,
        report="",
    )


def _build_comparisons(metrics: AccountMetrics, baseline: Baseline) -> list[FieldComparison]:
    rows: list[FieldComparison] = []
    price_delta = None if metrics.price is None else metrics.price - baseline.price
    rows.append(
        FieldComparison(
            name="价格",
            actual=metrics.price,
            baseline=baseline.price,
            delta=price_delta,
            passed=None if metrics.price is None else metrics.price <= baseline.price,
            comment="缺少数据"
            if metrics.price is None
            else ("不高于基准" if metrics.price <= baseline.price else f"高出 {price_delta:.0f} 元"),
        )
    )

    for field, label in FIELD_LABELS.items():
        actual = getattr(metrics, field)
        target = getattr(baseline, field)
        delta = None if actual is None else actual - target
        passed = None if actual is None else actual >= target
        if actual is None:
            comment = "缺少数据"
        elif passed:
            comment = f"达标，多 {delta}"
        else:
            comment = f"未达标，少 {abs(delta)}"
        rows.append(FieldComparison(name=label, actual=actual, baseline=target, delta=delta, passed=passed, comment=comment))
    return rows


def _score(metrics: AccountMetrics, baseline: Baseline) -> float:
    score = 0.0
    for field, weight in WEIGHTS.items():
        actual = getattr(metrics, field)
        target = getattr(baseline, field)
        if actual is None:
            continue
        score += weight * min(actual / target, 1.35)
    if metrics.skin_quality_score is not None:
        score += metrics.skin_quality_score
    return score


def _fair_price(metrics: AccountMetrics, baseline: Baseline, score: float) -> float:
    fair = baseline.price * (score / 100)
    penalty = 1.0
    if metrics.collections is not None and metrics.collections < baseline.collections:
        penalty -= 0.06 * (baseline.collections - metrics.collections)
    if metrics.wushuang is not None and metrics.wushuang < baseline.wushuang:
        penalty -= 0.04 * (baseline.wushuang - metrics.wushuang)
    if metrics.rare_legend is not None and metrics.rare_legend < baseline.rare_legend:
        penalty -= 0.03 * (baseline.rare_legend - metrics.rare_legend)
    if metrics.skins is not None and metrics.skins < 320:
        penalty -= 0.05
    return max(0.0, fair * max(0.70, penalty))


def _grade(value_ratio: float | None, rental_fit: str, missing_fields: list[str]) -> str:
    if missing_fields:
        return "信息不足"
    if value_ratio is None:
        return "信息不足"
    if "不太适合" in rental_fit:
        if value_ratio >= 1.35:
            return "低价备选"
        return "避开"
    if value_ratio >= 1.18:
        return "划算"
    if value_ratio >= 0.98:
        return "一般"
    if value_ratio >= 0.82:
        return "偏贵"
    return "避开"


def _rental_fit(metrics: AccountMetrics, purpose: str) -> str:
    if "出租" not in purpose and "共号" not in purpose:
        return "非共号/出租用途：按收藏和自用价值参考。"

    premium = (metrics.collections or 0) + (metrics.wushuang or 0) + (metrics.rare_legend or 0)
    legend = metrics.legend or 0
    skins = metrics.skins or 0
    quality = metrics.skin_quality_score or 0
    if premium >= 8 and legend >= 28 and skins >= 380:
        if quality < -2:
            return "勉强适合：数量达标，但命中的典藏/无双/珍传质量偏弱，买入价必须压低。"
        if quality >= 12:
            return "适合共号/出租：高价值皮肤数量和质量都接近或超过基准。"
        return "适合共号/出租：高价值皮肤和总皮肤规模都接近或超过基准。"
    if premium >= 5 and legend >= 20 and skins >= 300:
        if quality >= 12:
            return "勉强适合：数量略低于首选线，但命中多款高口碑皮肤，可做出租备选。"
        if quality < -2:
            return "不太适合：数量刚够备选线，但低价值或争议皮肤较多，展示吸引力不足。"
        return "勉强适合：可做出租备选，但买入价必须压低。"
    return "不太适合：高价值皮肤或总皮肤规模不足，出租吸引力偏弱。"


def _risks(
    metrics: AccountMetrics,
    baseline: Baseline,
    value_ratio: float | None,
    rental_fit: str,
) -> list[str]:
    risks = []
    if metrics.price is None:
        risks.append("没有售价，无法判断真实性价比。")
    if metrics.skins is not None and metrics.skins < baseline.skins * 0.75:
        risks.append("总皮肤数明显低于基准，账号厚度不足。")
    if metrics.collections is not None and metrics.collections < baseline.collections:
        risks.append("典藏数量低于朋友基准，稀有度有缺口。")
    if metrics.wushuang is not None and metrics.wushuang < baseline.wushuang:
        risks.append("无双数量低于朋友基准，出租展示卖点偏弱。")
    if metrics.weak_skins:
        risks.append("命中低价值或争议皮肤：" + "、".join(metrics.weak_skins[:4]) + "，不能只按数量加价。")
    if metrics.skin_quality_score is not None and metrics.skin_quality_score <= 0 and not metrics.top_skins:
        risks.append("未命中强势高口碑皮肤，当前估值主要依赖数量，买前要重点看具体皮肤列表。")
    if "不太适合" in rental_fit:
        risks.append("即使价格便宜，也不应作为共号/出租首选。")
    if value_ratio is not None and value_ratio < 0.82:
        risks.append("按当前字段估值明显低于售价，不建议追。")
    if not risks:
        risks.append("字段层面未见明显短板，仍需核验实名、找回包赔、段位、贵族等级和平台保障。")
    return risks


def _missing_fields(metrics: AccountMetrics) -> list[str]:
    missing = []
    if metrics.price is None:
        missing.append("价格")
    for field, label in FIELD_LABELS.items():
        if getattr(metrics, field) is None:
            missing.append(label)
    return missing


def _recommendation(grade: str, rental_fit: str, missing_fields: list[str]) -> str:
    if missing_fields:
        return f"先补齐字段再判断：缺少 {'、'.join(missing_fields)}。"
    if grade == "划算":
        return "可以重点看，进入核验环节；不要超过最高建议买入价。"
    if grade == "低价备选":
        return "只适合低价捡漏或自用，不适合作为出租首选。"
    if grade == "一般":
        return "可以作为备选，适合砍价或和其他账号横向比较。"
    if grade == "偏贵":
        return "除非有隐藏加分项，否则建议压价。"
    if "不太适合" in rental_fit:
        return "不建议作为共号/出租买入。"
    return "不建议买入，除非价格大幅下降。"
