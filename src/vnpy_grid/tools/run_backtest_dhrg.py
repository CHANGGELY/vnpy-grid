from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import sys

# 纭繚椤圭洰鏍圭洰褰曞湪 sys.path锛堣剼鏈粠 tools 涓嬭繍琛屾椂锛?
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vnpy.trader.constant import Interval
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode

from vnpy_grid.paths import get_output_dir
from vnpy_grid.strategies import DynamicHedgedRebateGridStrategy


def default(o):
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)


def main() -> None:
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol="ETHUSDT.GLOBAL",
        interval=Interval.MINUTE.value,
        start=datetime(2022, 8, 20),
        end=datetime(2025, 6, 15),
        rate=2.5e-5,
        slippage=0.2,
        size=1,
        pricetick=0.01,
        capital=1_000_000,
        mode=BacktestingMode.BAR,
    )

    setting = dict(
        grid_pct=0.0016,
        levels=5,
        long_size_init=1,
        short_size_init=1,
        min_order_size=1,
        max_individual_position_size=20,
        max_net_exposure_limit=50,
        max_account_drawdown_percent=0.5,
    )

    engine.add_strategy(DynamicHedgedRebateGridStrategy, setting)

    engine.load_data()
    engine.run_backtesting()

    print(f"limit_orders={len(engine.limit_orders)}, active_limit={len(engine.active_limit_orders)}, trades={len(engine.trades)}")

    df = engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    out_dir = get_output_dir("backtest_outputs_dhrg")
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / "equity_curve.csv", index=True, encoding="utf-8")
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=default), encoding="utf-8")

    print((out_dir / "stats.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()




