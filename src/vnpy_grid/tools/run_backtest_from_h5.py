from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingEngine, BacktestingMode

from vnpy_grid.paths import get_output_dir
from vnpy_grid.strategies import DynamicHedgedRebateGridStrategy


def infer_time_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["datetime", "time", "timestamp", "date"]
    lower = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name in lower:
            return lower[name]
    return None


def iter_bars_from_h5(
    path: Path,
    key: Optional[str],
    symbol: str,
    exchange: Exchange,
    chunksize: int = 200_000,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Iterable[BarData]:
    if not path.exists():
        raise FileNotFoundError(path)

    with pd.HDFStore(path, mode="r") as store:
        keys = store.keys()
        if not keys:
            raise RuntimeError("H5 文件没有任何数据")
        h5_key = key or next(k for k in keys if not k.endswith("/_i_table"))
        cursor = store.select(h5_key, chunksize=chunksize)
        for chunk in cursor:
            df = chunk
            time_col = infer_time_column(df)
            if time_col:
                ts = pd.to_datetime(df[time_col], errors="coerce", utc=True)
            else:
                ts = pd.to_datetime(df.index, errors="coerce", utc=True)

            if start:
                df = df[ts >= pd.Timestamp(start, tz="UTC")]
                ts = ts[ts >= pd.Timestamp(start, tz="UTC")]
            if end:
                df = df[ts <= pd.Timestamp(end, tz="UTC")]
                ts = ts[ts <= pd.Timestamp(end, tz="UTC")]

            for (_, row), dt in zip(df.iterrows(), ts):
                if pd.isna(dt):
                    continue
                yield BarData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt.to_pydatetime(),
                    interval=Interval.MINUTE,
                    volume=float(row.get("volume", 0.0)),
                    turnover=float(row.get("turnover", 0.0)),
                    open_price=float(row.get("open", row.get("open_price", 0.0))),
                    high_price=float(row.get("high", row.get("high_price", 0.0))),
                    low_price=float(row.get("low", row.get("low_price", 0.0))),
                    close_price=float(row.get("close", row.get("close_price", 0.0))),
                    gateway_name="H5",
                )


def run_backtest_from_h5(
    h5_path: Path,
    key: Optional[str],
    symbol: str,
    exchange: Exchange,
    start: Optional[datetime],
    end: Optional[datetime],
) -> None:
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=f"{symbol}.{exchange.value}",
        interval=Interval.MINUTE.value,
        start=start or datetime(1970, 1, 1),
        end=end or datetime.now(),
        rate=2.5e-5,
        slippage=0.2,
        size=1,
        pricetick=0.01,
        capital=1_000_000,
        mode=BacktestingMode.BAR,
    )
    engine.add_strategy(DynamicHedgedRebateGridStrategy, {})

    fed = 0
    for bar in iter_bars_from_h5(h5_path, key, symbol, exchange, start=start, end=end):
        engine.new_bar(bar)
        fed += 1
        if fed % 100_000 == 0:
            print(f"fed {fed} bars...")

    print(f"total bars fed: {fed}")
    engine.strategy.on_stop()

    df = engine.calculate_result()
    stats = engine.calculate_statistics(output=False)

    out_dir = get_output_dir("backtest_outputs_ethusdt_h5")
    out_dir.mkdir(exist_ok=True)

    df.to_csv(out_dir / "equity_curve.csv", index=True, encoding="utf-8")
    (out_dir / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest from HDF5 bars.")
    parser.add_argument("--h5", type=Path, required=True, help="HDF5 数据文件路径")
    parser.add_argument("--key", type=str, default=None, help="HDF5 key（默认使用第一个非索引key）")
    parser.add_argument("--symbol", type=str, default="ETHUSDT", help="合约代码")
    parser.add_argument("--exchange", type=str, default="GLOBAL", help="交易所枚举名")
    parser.add_argument("--start", type=str, default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="结束日期 YYYY-MM-DD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = datetime.fromisoformat(args.start) if args.start else None
    end = datetime.fromisoformat(args.end) if args.end else None
    exchange = Exchange[args.exchange]
    run_backtest_from_h5(args.h5, args.key, args.symbol, exchange, start, end)


if __name__ == "__main__":
    main()
