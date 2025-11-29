#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

"""
灏嗙幇鏈?H5锛堝彲鑳戒负 fixed 瀛樺偍锛夎浆鎹负 table 鏍煎紡锛屽苟寤虹珛 datetime 鏃堕棿绱㈠紩浠ヤ究楂樻晥 where 鏌ヨ涓庡垎鍧楄鍙栥€?浣跨敤鏂瑰紡锛圥owerShell锛夛細
  python -X utf8 tools\convert_h5_to_table.py --src "C:\path\ETHUSDT_1m_2019-11-01_to_2025-06-15.h5" --dst ETHUSDT_1m_table.h5 --key /klines --datetime-col datetime

娉ㄦ剰锛?- 杞崲閲囩敤鍒嗗潡璇诲彇锛坰tart/stop锛夛紝鍗曞潡榛樿 2e6 琛岋紱鑻ュ唴瀛樼揣寮犲彲璋冨皬銆?- 鑻ユ簮鏂囦欢宸茬粡鏄?table 鏍煎紡锛屽皢鐩存帴澶嶅埗涓烘柊鏂囦欢锛堜繚鐣?table锛夈€?"""


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=str)
    ap.add_argument("--dst", required=False, type=str, default=None)
    ap.add_argument("--key", required=False, type=str, default="/klines")
    ap.add_argument("--datetime-col", required=False, type=str, default=None, help="鏃堕棿鍒楀悕锛屾湭鎻愪緵鍒欒嚜鍔ㄦ帰娴?")
    ap.add_argument("--chunksize", required=False, type=int, default=2_000_000)
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"鉁?婧愭枃浠朵笉瀛樺湪: {src}")
        sys.exit(1)
    dst = Path(args.dst) if args.dst else src.with_name(src.stem + "_table.h5")

    with pd.HDFStore(src, mode="r") as s:
        keys = s.keys()
        if args.key not in keys:
            print(f"鈿狅笍 鎸囧畾 key {args.key} 涓嶅湪鏂囦欢涓紝鍙敤 keys: {list(keys)}")
            sys.exit(1)
        storer = s.get_storer(args.key)
        is_table = getattr(storer, "is_table", False)
        print(f"[婧愭枃浠禲 key={args.key} is_table={is_table} rows={getattr(storer, 'nrows', 'unknown')}")

        if is_table:
            # 鐩存帴澶嶅埗鏁翠釜 store 鐨勮 key 鍒版柊鏂囦欢
            print("[淇℃伅] 婧愬凡涓?table锛屾墽琛岄噸鍐欙紙鍘嬬缉锛夊鍒?")
            # 閫愬潡璇诲彇浠ラ伩鍏嶅唴瀛樺嘲鍊?
            start = 0
            total_rows = getattr(storer, "nrows", None)
            with pd.HDFStore(dst, mode="w", complevel=5, complib="blosc:zstd") as d:
                while True:
                    stop = start + args.chunksize
                    df = pd.read_hdf(str(src), key=args.key, start=start, stop=stop)
                    if df is None or len(df) == 0:
                        break
                    # 纭繚瀛樺湪 datetime 鍒?
                    dt_col = args.datetime_col
                    if not dt_col:
                        cols_lower = {c.lower(): c for c in df.columns}
                        for n in ("datetime", "time", "timestamp", "date"):
                            if n in cols_lower:
                                dt_col = cols_lower[n]
                                break
                    if not dt_col:
                        print("鉁?鏃犳硶璇嗗埆鏃堕棿鍒?")
                        sys.exit(1)
                    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
                    df = df.set_index(dt_col)
                    df = df.sort_index()
                    d.append(args.key, df, format="table", data_columns=True, index=True)
                    start = stop
            print(f"鉁?宸插啓鍑?table 鏂囦欢: {dst}")
        else:
            # fixed -> table
            print("[淇℃伅] 婧愪负 fixed锛屽皢鎸夎鍒囩墖杞崲涓?table")
            start = 0
            with pd.HDFStore(dst, mode="w", complevel=5, complib="blosc:zstd") as d:
                while True:
                    stop = start + args.chunksize
                    df = pd.read_hdf(str(src), key=args.key, start=start, stop=stop)
                    if df is None or len(df) == 0:
                        break
                    # 璇嗗埆鏃堕棿鍒?
                    dt_col = args.datetime_col
                    if not dt_col:
                        cols_lower = {c.lower(): c for c in df.columns}
                        for n in ("datetime", "time", "timestamp", "date"):
                            if n in cols_lower:
                                dt_col = cols_lower[n]
                                break
                    if not dt_col:
                        print("鉁?鏃犳硶璇嗗埆鏃堕棿鍒?")
                        sys.exit(1)
                    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
                    df = df.set_index(dt_col)
                    df = df.sort_index()
                    d.append(args.key, df, format="table", data_columns=True, index=True)
                    print(f"[鍐欏叆] rows {start}-{stop} -> appended")
                    start = stop
            print(f"鉁?宸插畬鎴?fixed->table 杞崲: {dst}")


if __name__ == "__main__":
    main()
