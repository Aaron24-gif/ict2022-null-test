"""CSV data layer for the public release.

The study was run on a private broker feed. This module is the seam: it gives the model the same interface the
private loader gave it, reading plain CSVs instead, so anyone can rerun the whole thing on their own data.

Put one file per instrument in data/, named <INSTRUMENT>.csv, with a header and these columns:

    timestamp,open,high,low,close,spread
    2018-01-02 00:00:00,15.50,15.52,15.49,15.51,0.30

  timestamp  broker local time, NO timezone suffix. The killzone windows in ict_model.py are expressed as
             minutes-from-midnight in the SAME clock, so if your feed is not New York time you must either
             convert the timestamps or edit KILLZONES. Getting this wrong silently moves the killzones.
  spread     in PRICE units, not points and not pips. If your export gives points, multiply by the point size
             (e.g. MT5 <SPREAD> on a 2-digit gold feed is points -> spread_price = spread_points * 0.01).
             If you have no spread column at all, set SPREAD_BP below and the loader synthesises a flat one.

Bar size: indices, metals and crypto were run on 1-minute bars; FX on 5-minute. Anything finer than the
structure rule (M5 or M15) works; the model resamples up internally.

A note you should not skip: a spread column of zeros will make this model look profitable. Most of the
positive results in the published study came from cost and fill assumptions, not from the pattern.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

START = "2018-01-01"
CAP = pd.Timestamp("2026-05-21 23:59")     # end of the sample; set to your own holdout boundary

SPREAD_BP = 1.5        # fallback spread in basis points of price, used only when the CSV has no spread column
COMMISSION = 0.0       # per-side commission in price units, added to the spread if your broker charges it
SWAP = 0.0             # overnight financing; the model is intraday, so it is unused here


def load(inst: str):
    """Return (bars, commission, swap). Bars: DatetimeIndex, columns open/high/low/close/spread."""
    f = DATA / f"{inst}.csv"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} not found. See the module docstring for the expected format, and data/HOWTO.md for "
            f"an MT5 export recipe.")
    d = pd.read_csv(f)
    cols = {c.lower().strip("<>"): c for c in d.columns}
    ts = cols.get("timestamp") or cols.get("date") or cols.get("time") or d.columns[0]
    d.index = pd.to_datetime(d[ts])
    d = d.rename(columns={v: k for k, v in cols.items()})
    keep = ["open", "high", "low", "close"]
    missing = [c for c in keep if c not in d.columns]
    if missing:
        raise ValueError(f"{f} is missing {missing}; got {list(d.columns)}")
    d = d[keep + (["spread"] if "spread" in d.columns else [])].astype(float)
    if "spread" not in d.columns:
        d["spread"] = d["close"] * SPREAD_BP * 1e-4
    d["spread"] = d["spread"] + COMMISSION
    d = d[~d.index.duplicated(keep="first")].sort_index().loc[START:str(CAP)]
    if d.empty:
        raise ValueError(f"{f} has no rows between {START} and {CAP}")
    if (d["spread"] <= 0).all():
        raise ValueError(f"{f} has a zero spread column. Fix it or delete it and let SPREAD_BP synthesise one "
                         f"- a zero-cost run of this model is meaningless.")
    return d, COMMISSION, SWAP


def resample(d, rule, offset=None):
    kw = {"offset": offset} if offset else {}
    b = d.resample(rule, label="left", closed="left", **kw).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    b["t_close"] = b.index + pd.Timedelta(rule)
    return b
