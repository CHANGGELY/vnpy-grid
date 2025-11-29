from __future__ import annotations
import os
import sys
from datetime import datetime, timezone

import pandas as pd

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database

# 浣跨敤锛?#   python -X utf8 tools/import_h5_to_vnpy_sqlite.py ETHUSDT_1m_2019-11-01_to_2025-06-15.h5 ETHUSDT.GLOBAL 1m
# 璇存槑锛?#   - 鐩存帴瀵煎叆浣犲凡鏈夌殑 HDF5 K绾垮埌 vn.py SQLite 鏁版嵁搴擄紝涓嶉渶瑕侀噸鏂颁笅杞姐€?#   - VT_SYMBOL 鐨勪氦鏄撴墍鏋氫妇蹇呴』鏄?vn.py 鍐呯疆锛堟棤 BINANCE/OKX锛夛紝鎺ㄨ崘鐢?GLOBAL 琛ㄧず澶栫洏/鍔犲瘑銆?#   - 鍒楀悕鍏煎锛歰pen/high/low/close/volume 鎴?Open/High/Low/Close/Volume锛涙椂闂村垪 index 鎴?columns 涓寘鍚?time/datetime/date銆?
COL_CANDIDATES = {
    "open": ["open", "Open", "OPEN", "o"],
    "high": ["high", "High", "HIGH", "h"],
    "low": ["low", "Low", "LOW", "l"],
    "close": ["close", "Close", "CLOSE", "c", "price"],
    "volume": ["volume", "Volume", "VOL", "vol", "v"],
}

TIME_CANDIDATES = [
    "datetime", "DateTime", "time", "Time", "date", "Date", "timestamp",
]

INTERVAL_MAP = {
    "1m": Interval.MINUTE,
    "1min": Interval.MINUTE,
    "60s": Interval.MINUTE,
}

def pick_col(df: pd.DataFrame, names: list[str]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df
    for c in TIME_CANDIDATES:
        if c in df.columns:
            dt = pd.to_datetime(df[c], utc=True, errors="coerce")
            df = df.copy()
            df.index = dt
            df.drop(columns=[c], inplace=True)
            return df
    dt = pd.to_datetime(df.iloc[:, 0], utc=True, errors="coerce")
    df = df.copy()
    df.index = dt
    return df


def row_to_bar(symbol: str, exchange: Exchange, interval: Interval, ts: pd.Timestamp, row: pd.Series) -> BarData:
    dt = ts.to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return BarData(
        symbol=symbol,
        exchange=exchange,
        datetime=dt,
        interval=interval,
        volume=float(row.get("volume", 0.0)) if not pd.isna(row.get("volume", 0.0)) else 0.0,
        turnover=0.0,
        open_interest=0.0,
        open_price=float(row["open"]),
        high_price=float(row["high"]),
        low_price=float(row["low"]),
        close_price=float(row["close"]),
        gateway_name="IMPORT",
    )


def import_h5(path: str, vt_symbol: str, interval_str: str) -> None:
    if "." not in vt_symbol:
        raise ValueError("VT_SYMBOL 蹇呴』褰㈠ SYMBOL.EXCHANGE锛屼緥濡?ETHUSDT.GLOBAL")
    symbol, exch_str = vt_symbol.split(".")
    try:
        exchange = Exchange(exch_str)
    except Exception:
        # 瀵逛簬鍔犲瘑绛夐潪鍐呯疆浜ゆ槗鎵€锛岀敤 GLOBAL
        exchange = Exchange.GLOBAL
        print(f"[WARN] 浜ゆ槗鎵€ {exch_str} 涓嶅湪鏋氫妇鍐咃紝浣跨敤 GLOBAL 浠ｆ浛")

    interval = INTERVAL_MAP.get(interval_str.lower())
    if interval is None:
        raise ValueError(f"Unsupported interval: {interval_str}")

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    df = pd.read_hdf(path)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("read_hdf did not return a DataFrame")

    df = ensure_datetime_index(df)
    df = df.sort_index()

    mapping = {}
    for k, cands in COL_CANDIDATES.items():
        col = pick_col(df, cands)
        if not col:
            raise KeyError(f"Missing column for {k}, candidates={cands}")
        mapping[k] = col
    df = df.rename(columns={
        mapping["open"]: "open",
        mapping["high"]: "high",
        mapping["low"]: "low",
        mapping["close"]: "close",
        mapping["volume"]: "volume",
    })

    df = df[~df.index.isna()]
    df = df.dropna(subset=["open", "high", "low", "close"])  # 閲忓彲绌?
    bars: list[BarData] = [row_to_bar(symbol, exchange, interval, ts, row) for ts, row in df.iterrows()]

    db = get_database()
    batch = 5000
    for i in range(0, len(bars), batch):
        ok = db.save_bar_data(bars[i:i + batch], stream=True)
        if not ok:
            raise RuntimeError(f"save_bar_data failed at batch {i}")
    print(f"Imported bars: {len(bars)} into {vt_symbol} {interval.value}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python -X utf8 tools/import_h5_to_vnpy_sqlite.py <h5_path> <VT_SYMBOL> <interval>")
        sys.exit(2)
    import_h5(sys.argv[1], sys.argv[2], sys.argv[3])
