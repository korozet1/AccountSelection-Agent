from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkinRule:
    name: str
    category: str
    tier: str
    score: float
    aliases: tuple[str, ...] = ()

    @property
    def display(self) -> str:
        return f"{self.name}（{self.category}{self.tier}）"


SKIN_RULES: tuple[SkinRule, ...] = (
    # 荣耀典藏
    SkinRule("安琪拉颠倒童话魔镜", "典藏", "T1", 10, ("安琪拉典藏", "颠倒童话魔镜")),
    SkinRule("关羽赤影疾锋", "典藏", "T1", 9, ("赤影疾锋",)),
    SkinRule("吕布怒海麟威", "典藏", "T1", 9, ("怒海麟威", "吕布千花缭乱", "千花缭乱")),
    SkinRule("花木兰九霄神辉", "典藏", "T1", 8, ("九霄神辉",)),
    SkinRule("小乔天鹅之梦", "典藏", "T1", 8, ("天鹅之梦",)),
    SkinRule("铠银白咏叹调", "典藏", "T2", 6, ("凯银白咏叹调", "银白咏叹调")),
    SkinRule("夏侯惇无限飓风号", "典藏", "T2", 6, ("无限飓风号",)),
    SkinRule("武则天倪克斯神谕", "典藏", "T2", 5, ("倪克斯神谕",)),
    SkinRule("李白鸣剑曳影", "典藏", "T2", 5, ("李白鸣剑・曳影", "鸣剑曳影", "鸣剑・曳影")),
    SkinRule("程咬金活力突击", "典藏", "T2", 5, ("活力突击",)),
    SkinRule("貂蝉幻阙歌", "典藏", "T3", 3, ("幻阙歌",)),
    SkinRule("伽罗最初的交响", "典藏", "T3", 3, ("伽罗炽翼辉光", "最初的交响")),
    SkinRule("韩信弑枪猎影", "典藏", "T3", 2, ("弑枪猎影",)),
    SkinRule("诸葛亮星域神启", "典藏", "T3", 2, ("星域神启",)),
    SkinRule("虞姬神鉴启示录", "典藏", "T4", -1, ("启明星使", "神鉴启示录")),
    SkinRule("孙悟空全息碎影", "典藏", "T4", -1, ("全息碎影",)),
    SkinRule("瑶拾光映像", "典藏", "T4", -1, ("瑶时之祈愿", "拾光映像")),
    SkinRule("孙尚香杀手不太冷", "典藏", "T5", -4, ("杀手不太冷",)),
    SkinRule("芈月大秦宣太后", "典藏", "T5", -4, ("大秦宣太后",)),
    SkinRule("鲁班七号星空梦想", "典藏", "T5", -4, ("星空梦想",)),
    # 珍品无双限定
    SkinRule("貂蝉馥梦繁花", "珍品无双", "S", 11, ("馥梦繁花",)),
    # 无双限定
    SkinRule("孙悟空无相", "无双", "T1", 8, ("无相",)),
    SkinRule("不知火舞花合斗", "无双", "T1", 8, ("花合斗",)),
    SkinRule("甄姬雪境奇遇", "无双", "T1", 8, ("甄姬冰雪奇遇", "雪境奇遇")),
    SkinRule("曜器灵螭龙剑", "无双", "T1", 8, ("曜七零神龙剑", "器灵螭龙剑")),
    SkinRule("吕布逐霄战戟", "无双", "T1.5", 7, ("吕布星剑", "逐霄战戟")),
    SkinRule("李白碎月剑心", "无双", "T2", 5, ("李白岁月剑心", "碎月剑心")),
    SkinRule("公孙离离恨烟", "无双", "T2", 5, ("公孙离李赫阡", "离恨烟")),
    SkinRule("小乔时之魔女", "无双", "T3", 2, ("时之魔女",)),
    SkinRule("韩信群星魔术团", "无双", "T3", 2, ("群星魔术团",)),
    SkinRule("诸葛亮天机白泽", "无双", "T3", 2, ("天机白泽",)),
    SkinRule("铠神罪", "无双", "T3", 2, ("凯神醉", "凯神罪", "铠神醉", "神罪")),
    SkinRule("瑶真我赫兹", "无双", "T4", -1, ("瑶甄嬛赫兹", "真我赫兹")),
    SkinRule("妲己青丘九尾", "无双", "T4", -1, ("青丘九尾",)),
    SkinRule("武则天神器明辉仪", "无双", "T5", -3, ("神奇女侠", "神器明辉仪")),
    # 珍品传说
    SkinRule("马可波罗怪盗基德", "珍传", "T0", 8, ("怪盗基德",)),
    SkinRule("铠东海龙王敖光", "珍传", "T1", 6, ("凯东海龙王敖光", "敖光")),
    SkinRule("瑶大耳狗之梦", "珍传", "T1", 6, ("大耳狗之梦",)),
    SkinRule("芈月西海龙王敖闰", "珍传", "T1", 6, ("里奥润", "敖闰", "芈月里奥润")),
    SkinRule("安琪拉库洛米之心", "珍传", "T2", 4, ("库洛米之心",)),
    SkinRule("伽罗沧流箭", "珍传", "T2", 4, ("沧流箭",)),
    SkinRule("张飞兔狲蓬尾", "珍传", "T2", 4, ("兔狲蓬尾", "兔狲・蓬尾")),
    SkinRule("孙策时之奇旅", "珍传", "T2", 4, ("时之奇旅",)),
    SkinRule("嫦娥器灵落星盏", "珍传", "T3", 2, ("器灵落星盏", "落星盏")),
    SkinRule("鲁班七号江户川柯南", "珍传", "T3", 2, ("江户川柯南",)),
    SkinRule("暃朽木白哉", "珍传", "T4", -2, ("朽木白哉",)),
    SkinRule("宫本武藏黑崎一护", "珍传", "T4", -3, ("黑崎一护",)),
    # 高口碑传说
    SkinRule("李信一念神魔", "传说", "S", 5, ("一念神魔",)),
    SkinRule("孙尚香末日机甲", "传说", "S", 4, ("末日机甲",)),
    SkinRule("李白凤求凰", "传说", "S", 4, ("凤求凰",)),
    SkinRule("夏侯惇霜北刀", "传说", "S", 4, ("双北刀", "霜北刀")),
    SkinRule("露娜霜月吟", "传说", "A", 3, ("霜月吟",)),
    SkinRule("兰陵王默契交锋", "传说", "A", 3, ("默契交锋",)),
    SkinRule("澜逐花归海", "传说", "A", 3, ("逐花归海",)),
    SkinRule("司马懿九山相柳", "传说", "A", 3, ("九山相柳",)),
    SkinRule("镜炽阳神光", "传说", "A", 3, ("炽阳神光",)),
    SkinRule("宫本武藏地狱之眼", "传说", "A", 3, ("地狱之眼",)),
    SkinRule("狄仁杰超时空战士", "传说", "C", -1, ("超时空战士",)),
)


def assess_skin_quality(text: str) -> dict[str, Any]:
    normalized = _normalize(text)
    matched: dict[str, SkinRule] = {}
    for rule in SKIN_RULES:
        names = (rule.name, *rule.aliases)
        if any(_normalize(name) in normalized for name in names):
            matched[rule.name] = rule

    rules = list(matched.values())
    raw_score = sum(rule.score for rule in rules)
    score = max(-10.0, min(35.0, raw_score))
    top_skins = [rule.display for rule in sorted(rules, key=lambda item: item.score, reverse=True) if rule.score >= 4]
    weak_skins = [rule.display for rule in sorted(rules, key=lambda item: item.score) if rule.score < 0]
    notes = []
    if rules:
        notes.append(f"命中皮肤质量表 {len(rules)} 款，原始质量分 {raw_score:.1f}。")
    else:
        notes.append("未命中已维护的高低价值皮肤名，暂按数量为主。")

    return {
        "skin_quality_score": round(score, 1),
        "top_skins": top_skins[:8],
        "weak_skins": weak_skins[:6],
        "skin_quality_notes": notes,
    }


def _normalize(value: str) -> str:
    return "".join(str(value or "").replace("・", "").replace("·", "").split()).lower()
