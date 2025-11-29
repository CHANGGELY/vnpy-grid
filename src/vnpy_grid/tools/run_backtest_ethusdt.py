from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
import json

from vnpy.trader.constant import Interval
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy
from vnpy_grid.paths import get_output_dir

# 鍥哄畾鍙傛暟锛堜笌鎴浘涓€鑷存垨鍚堢悊鍖栵級
VT_SYMBOL = "ETHUSDT.GLOBAL"
INTERVAL = Interval.MINUTE.value
START = datetime(2022, 8, 20)
END = datetime(2025, 6, 15)
RATE = 2.5e-5
SLIPPAGE = 0.2
SIZE = 1
PRICETICK = 0.01
CAPITAL = 1_000_000


def default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    return str(o)


def main() -> None:
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=VT_SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        rate=RATE,
        slippage=SLIPPAGE,
        size=SIZE,
        pricetick=PRICETICK,
        capital=CAPITAL,
        mode=BacktestingMode.BAR,
    )

    engine.add_strategy(AtrRsiStrategy, {})

    engine.load_data()
    print(f"Loaded bars: {len(engine.history_data)}")

    engine.run_backtesting()

    df = engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    # 杈撳嚭鐩綍
    out_dir = get_output_dir("backtest_outputs")
    out_dir.mkdir(exist_ok=True)

    df.to_csv(out_dir / "equity_curve.csv", index=True, encoding="utf-8")
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=default), encoding="utf-8")

    # 鍏抽敭鎸囨爣鎵撳嵃
    keys = [
        "鎬绘敹鐩婄巼", "骞村寲鏀剁泭鐜?", "鏈€澶у洖鎾?", "鑳滅巼", "鏀剁泭鍥炴挙姣?", "澶忔櫘姣旂巼", "鏃ュ潎鐩堜簭", "鎬绘垚浜ょ瑪鏁?"
    ]
    print("===== Backtest Statistics (key) =====")
    for k in keys:
        if k in stats:
            print(f"{k}: {stats[k]}")


if __name__ == "__main__":
    main()







