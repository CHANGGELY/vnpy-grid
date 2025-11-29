from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode

from vnpy_grid.paths import get_output_dir
from vnpy_grid.strategies import DynamicHedgedRebateGridStrategy

# Ensure project root on sys.path when executed directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def default(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def streaming_backtest(
    vt_symbol: str,
    interval: Interval,
    start: datetime,
    end: datetime,
    strategy_cls,
    setting: dict,
    rate: float = 2.5e-5,
    slippage: float = 0.2,
    size: float = 1,
    pricetick: float = 0.01,
    capital: int = 1_000_000,
    chunk_days: int = 15,
) -> dict:
    """
    Feed bar data chunk-by-chunk from the database to the backtesting engine.
    Useful for smoke-testing large datasets without exploding memory.
    """
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=interval.value,
        start=start,
        end=end,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        capital=capital,
        mode=BacktestingMode.BAR,
    )

    engine.add_strategy(strategy_cls, setting)
    engine.strategy.on_start()
    engine.strategy.trading = True

    symbol, exch = vt_symbol.split(".")
    exchange = Exchange(exch)

    db = get_database()
    cur = start
    total_days = max((end - start).days, 1)
    total_bars = 0

    while cur <= end:
        chunk_end = min(end, cur + timedelta(days=chunk_days))
        bars = db.load_bar_data(symbol, exchange, interval, cur, chunk_end)
        for bar in bars:
            engine.new_bar(bar)
        total_bars += len(bars)
        progress = min(100, int((chunk_end - start).days * 100 / total_days))
        print(f"[stream] {cur.date()} -> {chunk_end.date()} ({progress}%), bars={len(bars)}")
        cur = chunk_end + timedelta(minutes=1)

    engine.strategy.on_stop()

    df = engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    out_dir = get_output_dir("backtest_outputs_dhrg_stream")
    out_dir.mkdir(exist_ok=True)
    df.drop(columns=["trades"], errors="ignore").to_csv(
        out_dir / "equity_curve.csv", index=True, encoding="utf-8"
    )
    (out_dir / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, default=default),
        encoding="utf-8",
    )
    print(json.dumps(stats, ensure_ascii=False, default=default))
    return stats


if __name__ == "__main__":
    streaming_backtest(
        vt_symbol="ETHUSDT.GLOBAL",
        interval=Interval.MINUTE,
        start=datetime(2022, 8, 20),
        end=datetime(2022, 9, 20),
        strategy_cls=DynamicHedgedRebateGridStrategy,
        setting={
            "grid_pct": 0.0016,
            "levels": 5,
            "long_size_init": 0.01,
            "short_size_init": 0.01,
            "min_order_size": 0.01,
            "max_individual_position_size": 0.5,
            "max_net_exposure_limit": 2.0,
            "max_account_drawdown_percent": 0.5,
            "maker_rebate_rate": 0.00005,
            "taker_fee_rate": 0.0007,
            "assume_maker_for_resting_orders": True,
            "initial_equity_quote": 10_000.0,
        },
        chunk_days=10,
    )
