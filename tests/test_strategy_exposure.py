from vnpy_grid.strategies import DynamicHedgedRebateGridStrategy


def test_strategy_class_exposed() -> None:
    assert DynamicHedgedRebateGridStrategy.__name__ == "DynamicHedgedRebateGridStrategy"
