from pydantic import BaseModel, Field, field_validator


class EvaluateRequest(BaseModel):
    session_id: str | None = Field(default=None, description="会话 ID")
    url: str | None = Field(default=None, description="螃蟹平台商品链接或列表页链接")
    detail_text: str | None = Field(default=None, description="商品详情文案")
    purpose: str = Field(default="共号/出租变现", description="购买用途")
    max_items: int = Field(default=60, ge=1, le=200, description="列表页最多抓取商品数")
    min_price: float | None = Field(default=None, ge=0, description="最低预算")
    max_price: float | None = Field(default=None, ge=0, description="最高预算")
    use_model: bool = Field(default=True, description="是否使用模型复核最终报告")
    custom_rules: dict[str, str] | None = Field(default=None, description="用户自定义规则，如 skin_quality/system_prompt/baseline")

    @field_validator("url", "detail_text", mode="before")
    @classmethod
    def strip_empty(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def combined_input(self) -> str:
        parts = []
        if self.url:
            parts.append(f"商品链接：{self.url}")
        if self.detail_text:
            parts.append(f"商品详情：{self.detail_text}")
        parts.append(f"用途：{self.purpose}")
        parts.append(f"最多抓取：{self.max_items}")
        if self.min_price is not None or self.max_price is not None:
            parts.append(f"预算区间：{self.min_price or 0}-{self.max_price or '不限'}")
        parts.append(f"模型复核：{'开启' if self.use_model else '关闭'}")
        return "\n".join(parts)

