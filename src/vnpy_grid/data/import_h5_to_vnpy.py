"""
H5 -> vn.py SQLite importer for crypto minute bars.

Usage (PowerShell):
  .\\.venv\\Scripts\\Activate; python -X utf8 data/import_h5_to_vnpy.py \
    --path "C:\\Users\\chuan\\Desktop\\vnpy-grid\\ETHUSDT_1m_2019-11-01_to_2025-06-15.h5" \
    --symbol ETHUSDT --exchange BINANCE --interval 1m --dry-run

Then remove --dry-run to perform the actual import.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from pandas import HDFStore

from vnpy.trader.database import get_database
from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval


@dataclass
class ColumnMap:
    time: str
    open: str
    high: str
    low: str
    close: str
    volume: Optional[str] = None
    turnover: Optional[str] = None


TIME_CANDIDATES = [
    "datetime", "time", "timestamp", "date", "open_time", "start_time",
]
OPEN_CANDS = ["open", "open_price"]
HIGH_CANDS = ["high", "high_price"]
LOW_CANDS = ["low", "low_price"]
CLOSE_CANDS = ["close", "close_price"]
VOL_CANDS = ["volume", "vol", "base_volume", "qty", "amount"]
TURNOVER_CANDS = ["quote_volume", "turnover", "quote_asset_volume", "quote_amount"]


def infer_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in cols:
            return cols[cand]
    return None


def infer_columns(df: pd.DataFrame) -> ColumnMap:
    t = infer_column(df, TIME_CANDIDATES)
    o = infer_column(df, OPEN_CANDS)
    h = infer_column(df, HIGH_CANDS)
    l = infer_column(df, LOW_CANDS)
    c = infer_column(df, CLOSE_CANDS)
    if not all([t, o, h, l, c]):
        missing = [name for name, v in zip(["time","open","high","low","close"], [t,o,h,l,c]) if not v]
        raise ValueError(f"鏃犳硶鍦ㄦ暟鎹腑鎵惧埌蹇呴渶鍒? {missing}")
    v = infer_column(df, VOL_CANDS)
    to = infer_column(df, TURNOVER_CANDS)
    return ColumnMap(time=t, open=o, high=h, low=l, close=c, volume=v, turnover=to)


def parse_dt_col(s: pd.Series) -> pd.DatetimeIndex:
    # Handle numeric epoch (ns/ms/s) or parseable strings
    if pd.api.types.is_numeric_dtype(s):
        # heuristic by magnitude
        maxv = pd.to_numeric(s.dropna().astype("int64"), errors="coerce").max()
        unit = "s"
        if maxv and maxv > 1e14:
            unit = "ns"
        elif maxv and maxv > 1e11:
            unit = "ms"
        else:
            unit = "s"
        dt = pd.to_datetime(s, unit=unit, utc=True)
    else:
        dt = pd.to_datetime(s, utc=True, errors="coerce")
    if dt.isna().all():
        raise ValueError("鏃犳硶瑙ｆ瀽鏃堕棿鍒椾负鏈夋晥鐨勬椂闂存埑")
    return dt


def resolve_exchange(name: str) -> Exchange:
    # Prefer requested exchange if exists, else fallback to LOCAL
    try:
        ex = getattr(Exchange, name)
        if isinstance(ex, Exchange):
            return ex
    except Exception:
        pass
    return Exchange.LOCAL


def resolve_interval(text: str) -> Interval:
    t = text.strip().lower()
    if t in {"1m", "1min", "1minute", "minute", "m", "min"}:
        return Interval.MINUTE
    if t in {"1h", "hour", "h"}:
        return Interval.HOUR
    if t in {"1d", "day", "d", "daily"}:
        return Interval.DAILY
    raise ValueError(f"涓嶆敮鎸佺殑鍛ㄦ湡: {text}")


def chunk_iter(df: pd.DataFrame, size: int) -> Iterable[pd.DataFrame]:
    n = len(df)
    for i in range(0, n, size):
        yield df.iloc[i:i+size]


def build_bars(
    df: pd.DataFrame,
    cmap: ColumnMap,
    symbol: str,
    exchange: Exchange,
    interval: Interval,
    gateway_name: str = "BACKTEST",
) -> List[BarData]:
    dt_idx = parse_dt_col(df[cmap.time])
    opens = pd.to_numeric(df[cmap.open], errors="coerce")
    highs = pd.to_numeric(df[cmap.high], errors="coerce")
    lows = pd.to_numeric(df[cmap.low], errors="coerce")
    closes = pd.to_numeric(df[cmap.close], errors="coerce")
    vols = pd.to_numeric(df[cmap.volume], errors="coerce") if cmap.volume else None
    tos = pd.to_numeric(df[cmap.turnover], errors="coerce") if cmap.turnover else None

    bars: List[BarData] = []
    for i in range(len(df)):
        dt = dt_idx.iloc[i]
        if pd.isna(dt):
            continue
        # ensure timezone-aware UTC datetime
        dt_py = dt.to_pydatetime().replace(tzinfo=timezone.utc)
        o = float(opens.iloc[i]) if pd.notna(opens.iloc[i]) else 0.0
        h = float(highs.iloc[i]) if pd.notna(highs.iloc[i]) else 0.0
        l = float(lows.iloc[i]) if pd.notna(lows.iloc[i]) else 0.0
        c = float(closes.iloc[i]) if pd.notna(closes.iloc[i]) else 0.0
        v = float(vols.iloc[i]) if (vols is not None and pd.notna(vols.iloc[i])) else 0.0
        to = float(tos.iloc[i]) if (tos is not None and pd.notna(tos.iloc[i])) else 0.0
        bar = BarData(
            gateway_name=gateway_name,
            symbol=symbol,
            exchange=exchange,
            datetime=dt_py,
            interval=interval,
            volume=v,
            turnover=to,
            open_interest=0.0,
            open_price=o,
            high_price=h,
            low_price=l,
            close_price=c,
        )
        bars.append(bar)
    return bars


def import_h5(
    path: str,
    symbol: str,
    exchange_name: str,
    interval_text: str,
    key: Optional[str],
    chunk_rows: int = 200_000,
    dry_run: bool = False,
) -> None:
    db = get_database()
    exchange = resolve_exchange(exchange_name)
    interval = resolve_interval(interval_text)

    if exchange is Exchange.LOCAL and exchange_name.upper() != "LOCAL":
        print(f"[璀﹀憡] Exchange.{exchange_name.upper()} 涓嶅瓨鍦紝涓存椂浣跨敤 Exchange.LOCAL 瀵煎叆锛堜笉褰卞搷鍥炴祴鍔熻兘锛夈€?")

    with HDFStore(path, mode="r") as store:
        keys = store.keys()
        if not keys:
            raise RuntimeError("H5 鏂囦欢涓湭鍙戠幇浠讳綍鏁版嵁闆?keys")
        use_key = key or keys[0]
        if use_key not in keys:
            raise RuntimeError(f"鎸囧畾鐨?key={use_key} 涓嶅瓨鍦紝H5 keys={keys}")

        # Try chunked table first
        iterator = None
        try:
            iterator = store.select(use_key, chunksize=chunk_rows)
        except Exception:
            iterator = None

        def process_df(df: pd.DataFrame, preview: bool = False) -> None:
            cmap = infer_columns(df)
            if preview or dry_run:
                print("[棰勮] 鍒楁槧灏?", cmap)
                print(df.head(5).to_string())
                return
            # build and save in chunks to control memory
            total = 0
            for part in chunk_iter(df, 200_000):
                bars = build_bars(part, cmap, symbol=symbol, exchange=exchange, interval=interval)
                if bars:
                    db.save_bar_data(bars)
                    total += len(bars)
                    print(f"宸插啓鍏?{total} 鏉?..")
            print(f"鍐欏叆瀹屾垚锛屾€昏 {total} 鏉°€?")

        if iterator is not None:
            # Consume first chunk for preview
            first = next(iterator)
            process_df(first, preview=True)
            if dry_run:
                return
            # Save first chunk
            process_df(first, preview=False)
            # Continue remaining chunks
            for chunk in iterator:
                process_df(chunk, preview=False)
        else:
            df = store.get(use_key)
            process_df(df, preview=True)
            if dry_run:
                return
            process_df(df, preview=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="H5 鏂囦欢缁濆璺緞")
    ap.add_argument("--symbol", required=True, help="鍚堢害绗﹀彿锛屽 ETHUSDT")
    ap.add_argument("--exchange", required=True, help="浜ゆ槗鎵€鏍囪瘑锛屽 BINANCE锛涜嫢涓嶅瓨鍦紝鍒欏洖閫€涓?LOCAL")
    ap.add_argument("--interval", required=True, help="鍛ㄦ湡锛屽 1m/1h/1d")
    ap.add_argument("--key", required=False, help="H5 鍐呴儴鏁版嵁闆?key锛屼笉鎸囧畾鍒欎娇鐢ㄧ涓€涓?")
    ap.add_argument("--chunk", type=int, default=200_000, help="姣忔壒琛屾暟锛堣〃鏍煎紡 H5 鏈夋晥锛?")
    ap.add_argument("--dry-run", action="store_true", help="浠呴瑙堝垪鏄犲皠鍜屾牱渚嬶紝涓嶅啓鏁版嵁搴?")
    args = ap.parse_args()

    import_h5(
        path=args.path,
        symbol=args.symbol,
        exchange_name=args.exchange,
        interval_text=args.interval,
        key=args.key,
        chunk_rows=args.chunk,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

