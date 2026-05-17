import re
from typing import Any

from app.models.account import AccountMetrics
from app.tools.skin_quality import assess_skin_quality


CN_NUMBERS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def metrics_from_dict(data: dict[str, Any]) -> AccountMetrics:
    return AccountMetrics(**data)


def extract_account_metrics(text: str) -> AccountMetrics:
    normalized = _normalize_text(text or "")
    notes: list[str] = []
    skin_quality = assess_skin_quality(text or "")

    price = _extract_price(normalized)
    collections = _extract_count(normalized, [r"典藏", r"荣耀典藏"])
    wushuang = _extract_count(normalized, [r"(?<!珍品)无双限定", r"(?<!珍品)无双"])
    rare_legend = _extract_count(normalized, [r"珍品传说", r"珍传"])
    legend = _extract_count(normalized, [r"(?<!珍品)传说(?!体验|卡|积分|令牌)"])
    skins = _extract_count(normalized, [r"皮肤", r"总皮"])
    heroes = _extract_count(normalized, [r"英雄"])
    rank = _extract_rank(normalized)

    if price is None:
        notes.append("未明确识别到售价。")
    if skins is None:
        notes.append("未明确识别到总皮肤数。")
    if collections is None and "典藏" not in normalized:
        notes.append("未明确识别到典藏数量。")

    return AccountMetrics(
        price=price,
        collections=collections,
        wushuang=wushuang,
        rare_legend=rare_legend,
        legend=legend,
        skins=skins,
        heroes=heroes,
        rank=rank,
        skin_quality_score=skin_quality["skin_quality_score"],
        top_skins=skin_quality["top_skins"],
        weak_skins=skin_quality["weak_skins"],
        skin_quality_notes=skin_quality["skin_quality_notes"],
        notes=notes,
    )


def _normalize_text(text: str) -> str:
    replacements = {
        "荣耀水晶": "典藏",
        "无双皮": "无双",
        "珍品传说皮肤": "珍品传说",
        "传说皮肤": "传说",
        "款皮肤": "皮肤",
        "总皮肤": "皮肤",
    }
    normalized = text.replace("：", ":").replace("，", ",").replace("。", ".")
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _extract_price(text: str) -> float | None:
    patterns = [
        r"(?:售价|价格|标价|到手|卖价|出价|¥|￥)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:元|块|rmb)?",
        r"(\d+(?:\.\d+)?)\s*(?:元|块|rmb)",
    ]
    candidates = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            value = float(match.group(1))
            if 50 <= value <= 50000:
                candidates.append(value)
    return candidates[0] if candidates else None


def _extract_count(text: str, keywords: list[str]) -> int | None:
    for keyword in keywords:
        patterns = [
            rf"{keyword}\s*[:：]?\s*(\d+|[零一二两三四五六七八九十]+)",
            rf"{keyword}\s*(\d+|[零一二两三四五六七八九十]+)\s*(?:个|款|套|枚|颗|张)?\s*(?:左右|余|多)?",
            rf"(\d+|[零一二两三四五六七八九十]+)\s*(?:个|款|套|枚|颗|张)?\s*(?:左右|余|多)?\s*{keyword}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return _parse_int(match.group(1))
    return None


def _parse_int(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    if value in CN_NUMBERS:
        return CN_NUMBERS[value]
    if value.startswith("十"):
        return 10 + CN_NUMBERS.get(value[1:], 0)
    if value.endswith("十"):
        return CN_NUMBERS.get(value[:-1], 0) * 10
    if "十" in value:
        left, right = value.split("十", 1)
        return CN_NUMBERS.get(left, 1) * 10 + CN_NUMBERS.get(right, 0)
    return None


def _extract_rank(text: str) -> str | None:
    ranks = ["荣耀王者", "无双王者", "最强王者", "星耀", "钻石", "铂金", "黄金"]
    for rank in ranks:
        if rank in text:
            return rank
    return None
