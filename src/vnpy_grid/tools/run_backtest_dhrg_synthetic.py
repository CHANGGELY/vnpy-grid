from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
import math
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 寮哄埗鍔犺浇琛ヤ竵锛堟祦寮忓拰鍐呭瓨浼樺寲鍦ㄨ繖閲屼笉渚濊禆DB锛屼絾鎴戜滑楠岃瘉绛栫暐鍜岃绠楅摼璺級
import patch_ctabacktester  # noqa: F401

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode

from vnpy_grid.paths import get_output_dir
from vnpy_grid.strategies import DynamicHedgedRebateGridStrategy


def default(o):
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)


def gen_synthetic_minute_bars(
    start_dt: datetime,
    end_dt: datetime,
    start_price: float = 1600.0,
    mu: float = 0.0,
    sigma: float = 0.002,
    seed: int = 42,
):
    """鐢熸垚绠€鍗曠殑鍑犱綍甯冩湕杩愬姩浠锋牸锛屽苟鏋勯€?m K绾?"""
    random.seed(seed)
    cur = start_price
    t = start_dt
    bars = []
    
    while t <= end_dt:
        # 璺宠繃闈炰氦鏄撴椂闂达紙杩欓噷绠€鍗曡捣瑙侊紝姣忓垎閽熼兘鐢熸垚锛?
        ret = mu + sigma * random.gauss(0, 1)
        nxt = max(1e-6, cur * math.exp(ret))
        high = max(cur, nxt) * (1 + 0.0005)
        low = min(cur, nxt) * (1 - 0.0005)
        open_ = cur
        close = nxt
        vol = 10.0  # 浠绘剰璁剧疆

        bar = BarData(
            symbol="SYNTH",
            exchange=Exchange.GLOBAL,
            datetime=t,
            interval=Interval.MINUTE,
            volume=vol,
            open_price=open_,
            high_price=high,
            low_price=low,
            close_price=close,
            gateway_name="SYN",
        )
        bars.append(bar)
        cur = nxt
        t = t + timedelta(minutes=1)
    return bars


def synthetic_backtest():
    vt_symbol = "SYNTH.GLOBAL"
    interval = Interval.MINUTE
    start = datetime(2022, 8, 1)
    end = datetime(2022, 8, 7)  # 7澶╋紝~10080鏍筨ar

    setting = dict(
        grid_pct=0.0016,
        levels=5,
        long_size_init=0.01,
        short_size_init=0.01,
        min_order_size=0.01,
        max_individual_position_size=0.5,
        max_net_exposure_limit=2.0,
        max_account_drawdown_percent=0.5,
    )

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=interval.value,
        start=start,
        end=end,
        rate=2.5e-5,
        slippage=0.2,
        size=1,
        pricetick=0.01,
        capital=1_000_000,
        mode=BacktestingMode.BAR,
    )
    engine.add_strategy(DynamicHedgedRebateGridStrategy, setting)

    # 鍚姩绛栫暐
    engine.strategy.on_start()
    engine.strategy.trading = True

    # 鐢熸垚骞舵帹閫佸悎鎴怋ar
    bars = gen_synthetic_minute_bars(start, end, start_price=1600)
    # 淇bar鐨別xchange涓篏LOBAL浠ゅ尮閰峷t_symbol
    for i, b in enumerate(bars, 1):
        b.exchange = Exchange.GLOBAL
        engine.new_bar(b)
        if i % 1000 == 0:
            print(f"[synthetic] fed {i}/{len(bars)} bars")

    engine.strategy.on_stop()

    df = engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    out_dir = get_output_dir("backtest_outputs_dhrg_synth")
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / "equity_curve.csv", index=True, encoding="utf-8")
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=default), encoding="utf-8")

    brief_keys = [
        "total_return", "annual_return", "sharpe_ratio", "max_drawdown",
        "max_drawdown_duration", "total_trade_count",
    ]
    brief = {k: stats.get(k) for k in brief_keys}
    print("=== Synthetic Backtest Brief ===")
    print(json.dumps(brief, ensure_ascii=False, indent=2, default=default))


if __name__ == "__main__":
    synthetic_backtest()




