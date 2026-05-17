from app.tools.extractor import extract_account_metrics
from app.tools.reporter import build_batch_markdown_report
from app.tools.scorer import evaluate_account


def test_batch_report_contains_ranking():
    metrics = extract_account_metrics("售价588元，典藏2 传说10 皮肤349")
    result = evaluate_account(metrics)
    report = build_batch_markdown_report(
        [
            {
                "title": "典藏2 传说10 皮肤349",
                "url": "https://www.pxb7.com/product/1",
                "metrics": metrics.model_dump(),
                "evaluation": result.model_dump(),
            }
        ]
    )

    assert "螃蟹列表页筛选报告" in report
    assert "最高买入" in report

