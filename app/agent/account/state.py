from typing import Annotated, Any, TypedDict
import operator


class AccountAgentState(TypedDict, total=False):
    input: str
    url: str | None
    detail_text: str | None
    purpose: str
    max_items: int
    min_price: float | None
    max_price: float | None
    use_model: bool
    custom_rules: dict[str, str] | None
    plan: list[str]
    past_steps: Annotated[list[tuple[str, str]], operator.add]
    raw_text: str
    metrics: dict[str, Any]
    evaluation: dict[str, Any]
    listings: list[dict[str, Any]]
    ranked_listings: list[dict[str, Any]]
    model_review: str
    preview_report: str
    response: str
    progress_queue: Any
    warnings: Annotated[list[str], operator.add]
