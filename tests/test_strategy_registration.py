from vnpy_ctastrategy.engine import CtaEngine
from vnpy.trader.engine import MainEngine


def test_strategy_registered() -> None:
    main_engine = MainEngine()
    cta_engine = CtaEngine(main_engine, {})
    cta_engine.load_strategy_class()
    assert "DynamicHedgedRebateGridStrategy" in cta_engine.classes
