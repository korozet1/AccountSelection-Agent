from pydantic import BaseModel, Field


class AccountMetrics(BaseModel):
    price: float | None = Field(default=None, description="售价，单位元")
    collections: int | None = Field(default=None, description="荣耀典藏数量")
    wushuang: int | None = Field(default=None, description="无双限定数量")
    rare_legend: int | None = Field(default=None, description="珍品传说数量")
    legend: int | None = Field(default=None, description="传说皮肤数量")
    skins: int | None = Field(default=None, description="总皮肤数量")
    heroes: int | None = Field(default=None, description="英雄数量")
    rank: str | None = Field(default=None, description="段位")
    skin_quality_score: float | None = Field(default=None, description="命中的高低价值皮肤质量加减分")
    top_skins: list[str] = Field(default_factory=list, description="命中的高价值皮肤")
    weak_skins: list[str] = Field(default_factory=list, description="命中的低价值或争议皮肤")
    skin_quality_notes: list[str] = Field(default_factory=list, description="皮肤质量规则说明")
    notes: list[str] = Field(default_factory=list)


class Baseline(BaseModel):
    price: float = 1300.0
    collections: int = 3
    wushuang: int = 3
    rare_legend: int = 2
    legend: int = 30
    skins: int = 400


class FieldComparison(BaseModel):
    name: str
    actual: int | float | str | None
    baseline: int | float | str | None
    delta: int | float | None
    passed: bool | None
    comment: str


class EvaluationResult(BaseModel):
    metrics: AccountMetrics
    baseline: Baseline
    comparisons: list[FieldComparison]
    fair_price: float
    max_buy_price: float
    value_ratio: float | None
    score: float
    grade: str
    recommendation: str
    rental_fit: str
    risks: list[str]
    missing_fields: list[str]
    report: str
