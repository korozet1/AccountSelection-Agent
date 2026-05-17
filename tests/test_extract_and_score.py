from app.tools.extractor import extract_account_metrics
from app.tools.scorer import evaluate_account


def test_extract_friend_baseline_text():
    metrics = extract_account_metrics("售价1300元，3典藏，3无双，2珍品传说，30传说，400左右皮肤")

    assert metrics.price == 1300
    assert metrics.collections == 3
    assert metrics.wushuang == 3
    assert metrics.rare_legend == 2
    assert metrics.legend == 30
    assert metrics.skins == 400


def test_evaluate_baseline_is_not_bad():
    metrics = extract_account_metrics("售价1300元，3典藏，3无双，2珍品传说，30传说，400皮肤")
    result = evaluate_account(metrics)

    assert result.grade in {"一般", "划算"}
    assert result.max_buy_price > 1000
    assert not result.missing_fields


def test_expensive_low_inventory_should_avoid():
    metrics = extract_account_metrics("售价1500元，1典藏，0无双，0珍品传说，12传说，220皮肤")
    result = evaluate_account(metrics)

    assert result.grade in {"偏贵", "避开"}
    assert result.value_ratio is not None
    assert result.value_ratio < 1


def test_extract_adjacent_rare_and_wushuang_counts():
    metrics = extract_account_metrics("珍品传说4 无双3 典藏4 传说17 皮肤145")

    assert metrics.rare_legend == 4
    assert metrics.wushuang == 3
    assert metrics.collections == 4
    assert metrics.legend == 17
