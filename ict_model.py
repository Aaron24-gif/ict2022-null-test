"""
ICT 2022 MENTORSHIP MODEL -- event-driven state machine (PREREG.md, Stage 1 frozen spec + named variants).

Sequence, from the book (p249-250):
    liquidity raid -> displacement -> MSS -> FVG beyond the 50% of the displacement range -> limit entry in the FVG

State machine per symbol:
    NONE -> RAIDED -> DISPLACED -> MSS_OK -> FVG_OK -> ORDER -> POSITION -> (COMPLETED | EXPIRED | CANCELLED)

Causality, enforced structurally rather than by convention:
  * every liquidity level carries `known_from`; a raid on bar i may only use levels with known_from <= i-1
  * pivots need their right-side lag before they exist
  * an FVG on bar f uses only f-2, f-1, f
  * an order created at the close of f can fill no earlier than f+1
  * stop-first when a bar touches both stop and target; a stop takes the gap; a limit fills at its level
  * the loaders cap at 2026-05-21 -- the sealed holdout is never read

Usage:  python ict_model.py <INSTRUMENT> [variant=stage1]
        python ict_model.py summary
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import data as MM                                        # noqa: E402

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
CAP = pd.Timestamp("2026-05-21 23:59")
SEL_END = pd.Timestamp("2023-01-01")

# -- the book's killzones, New York local (p95) ---------------------------------------------
KILLZONES = {"LONDON": (2 * 60, 5 * 60), "NY": (7 * 60, 10 * 60)}
PAIRS = {"M15>M1": ("15min", 1), "M5>M1": ("5min", 1)}

STAGE1 = dict(raid="V1", disp="V1", mss="V1", entry="V1", stop="V1", tgt="V1",
              pivot_lag=2, min_fvg_atr=0.20, disp_window=5, mss_window=10, fvg_window=5,
              max_setup_bars=20, order_ttl=10, stop_buf_atr=0.25, min_rr=1.5, def_rr=2.0, max_rr=4.0,
              max_stop_atr=3.0)


@dataclass
class Setup:
    side: int                       # +1 long, -1 short
    raid_bar: int
    raid_level: float
    raid_extreme: float
    structure_ref: float
    state: str = "RAIDED"
    disp_bar: int | None = None
    mss_bar: int | None = None
    fvg_bar: int | None = None
    fvg_lo: float = 0.0
    fvg_hi: float = 0.0
    disp_lo: float = 0.0            # displacement range, for the 50% equilibrium
    disp_hi: float = 0.0
    meta: dict = field(default_factory=dict)


def atr(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()


def fractals(h, l, k):
    """Confirmed 2-bar fractals (programme convention). Returns arrays of (idx, price), usable from idx+k."""
    n = len(h)
    hi, lo = [], []
    for i in range(k, n - k):
        if h[i] == max(h[i - k:i + k + 1]) and h[i] > max(h[i - k:i]) and h[i] > max(h[i + 1:i + k + 1]):
            hi.append((i, h[i]))
        if l[i] == min(l[i - k:i + k + 1]) and l[i] < min(l[i - k:i]) and l[i] < min(l[i + 1:i + k + 1]):
            lo.append((i, l[i]))
    return hi, lo


def build_levels(idx, h, l, k):
    """Liquidity pools with an explicit known_from bar: session highs/lows, previous day H/L, confirmed fractals."""
    day = idx.normalize()
    mins = np.asarray(idx.hour * 60 + idx.minute)
    pools = []                                                  # (known_from, price, side)  side +1 = BSL above
    days = pd.Index(sorted(set(day)))
    prev = None
    for d in days:
        sl = np.nonzero(np.asarray(day == d))[0]
        if not len(sl):
            continue
        if prev is not None and len(prev):
            pools.append((sl[0], float(h[prev].max()), +1))     # previous day high
            pools.append((sl[0], float(l[prev].min()), -1))     # previous day low
        asia = sl[(mins[sl] >= 20 * 60) | (mins[sl] < 0)]       # 20:00-23:59 NY (book's Asia killzone)
        if len(asia) > 10:
            kn = asia[-1] + 1
            if kn < len(idx):
                pools.append((kn, float(h[asia].max()), +1))
                pools.append((kn, float(l[asia].min()), -1))
        lon = sl[(mins[sl] >= 2 * 60) & (mins[sl] < 5 * 60)]    # London session high/low
        if len(lon) > 10:
            kn = lon[-1] + 1
            if kn < len(idx):
                pools.append((kn, float(h[lon].max()), +1))
                pools.append((kn, float(l[lon].min()), -1))
        prev = sl
    fh, fl = fractals(h, l, k)
    for i, p in fh:
        pools.append((i + k + 1, float(p), +1))
    for i, p in fl:
        pools.append((i + k + 1, float(p), -1))
    pools.sort(key=lambda x: x[0])
    return pools


def run_instrument(inst, pair="M15>M1", kz="NY", cfg=None, verbose=True, base=None):
    cfg = dict(STAGE1, **(cfg or {}))
    if base is None:
        base, _, _ = MM.load(inst)
        base = base.loc[:CAP]
    rule, _ = PAIRS[pair]
    sb = base.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "max"}).dropna()
    o, h, l, c, sp = (sb[k].to_numpy(float) for k in ("open", "high", "low", "close", "spread"))
    idx = sb.index
    A = atr(h, l, c)
    med_rng = pd.Series(h - l).rolling(20).median().to_numpy()
    mins = np.asarray(idx.hour * 60 + idx.minute)
    k = cfg["pivot_lag"]
    pools = build_levels(idx, h, l, k)
    p_kn = np.array([x[0] for x in pools]); p_px = np.array([x[1] for x in pools]); p_sd = np.array([x[2] for x in pools])
    MAX_AGE = 1000                                     # structure bars a pool stays live
    _cache = {"at": -1, "bsl": (np.empty(0), np.empty(0)), "ssl": (np.empty(0), np.empty(0))}

    def pools_at(i):
        """Sorted (price) views of pools knowable at i-1 and not older than MAX_AGE. Rebuilt every 256 bars --
        the previous version filtered the whole pool list on every bar, which is what made this unrunnable."""
        if i - _cache["at"] >= 256:
            m = (p_kn <= i - 1) & (i - p_kn <= MAX_AGE)
            for side, key in ((+1, "bsl"), (-1, "ssl")):
                sel = m & (p_sd == side)
                px = np.sort(p_px[sel])
                _cache[key] = (px, px)
            _cache["at"] = i
        return _cache["bsl"][0], _cache["ssl"][0]
    fh, fl = fractals(h, l, k)
    hi_idx = np.array([i for i, _ in fh]); hi_px = np.array([p for _, p in fh])
    lo_idx = np.array([i for i, _ in fl]); lo_px = np.array([p for _, p in fl])
    z0, z1 = KILLZONES[kz]
    su: Setup | None = None
    order = None
    trades = []
    counters = dict(raids=0, displaced=0, mss=0, fvg=0, orders=0, fills=0)

    for i in range(30, len(sb)):
        if not np.isfinite(A[i]) or A[i] <= 0:
            continue

        # -- 1. fill / manage an existing order or position on THIS bar (created no later than i-1)
        if order is not None and order["fill_from"] <= i:
            lim = order["limit"]
            hit = (l[i] <= lim) if order["side"] > 0 else (h[i] + sp[i] >= lim)
            if hit:
                fill = (min(lim, o[i]) if order["side"] > 0 else max(lim, o[i] + sp[i]))
                stop, tgt = order["stop"], order["target"]
                unit = abs(fill - stop)
                if unit > 2 * sp[i]:
                    counters["fills"] += 1
                    R, reason, xbar = None, None, None
                    for j in range(i, min(len(sb), i + 500)):
                        if order["side"] > 0:
                            hit_sl, hit_tp = l[j] <= stop, h[j] >= tgt
                        else:
                            hit_sl, hit_tp = h[j] + sp[j] >= stop, l[j] + sp[j] <= tgt
                        if hit_sl:                                          # stop first, gap-honest
                            px = min(stop, o[j]) if order["side"] > 0 else max(stop, o[j] + sp[j])
                            R, reason, xbar = order["side"] * (px - fill) / unit, "STOP", j; break
                        if hit_tp:
                            R, reason, xbar = order["side"] * (tgt - fill) / unit, "TP", j; break
                    if R is None:
                        j = min(len(sb), i + 500) - 1
                        px = c[j] + (0.0 if order["side"] > 0 else sp[j])
                        R, reason, xbar = order["side"] * (px - fill) / unit, "TIMEOUT", j
                    trades.append(dict(inst=inst, pair=pair, kz=kz, side=order["side"], raid_bar=order["raid_bar"],
                                       entry_time=idx[i], exit_time=idx[xbar], fill=fill, stop=stop, target=tgt,
                                       unit=unit, R=R, reason=reason, rr=abs(tgt - fill) / unit))
                order = None; su = None
            elif i > order["expiry"] or (order["side"] > 0 and c[i] < order["invalid"]) or \
                    (order["side"] < 0 and c[i] > order["invalid"]):
                order = None; su = None

        # -- 2. raid detection (only pools known before this bar), inside the killzone
        in_kz = z0 <= mins[i] < z1
        if su is None and order is None and in_kz:
            bsl, ssl = pools_at(i)
            for side in (+1, -1):
                if side > 0:                                   # nearest BSL above yesterday's close, breached today
                    a = np.searchsorted(bsl, c[i - 1], "right"); b = np.searchsorted(bsl, h[i], "right")
                    if b <= a:
                        continue
                    lvl = float(bsl[a])
                else:
                    a = np.searchsorted(ssl, l[i], "left"); b = np.searchsorted(ssl, c[i - 1], "left")
                    if b <= a:
                        continue
                    lvl = float(ssl[b - 1])
                if cfg["raid"] == "V2":                                  # Qwen: same-bar close back through
                    if not ((c[i] < lvl) if side > 0 else (c[i] > lvl)):
                        continue
                trade_side = -side                                        # raid BSL -> short, raid SSL -> long
                ext = h[i] if side > 0 else l[i]
                if trade_side > 0:
                    prior = hi_px[(hi_idx + k < i)]
                    ref = float(prior[-1]) if len(prior) else np.nan
                    ok = np.isfinite(ref) and ref > l[i]
                else:
                    prior = lo_px[(lo_idx + k < i)]
                    ref = float(prior[-1]) if len(prior) else np.nan
                    ok = np.isfinite(ref) and ref < h[i]
                if not ok:
                    continue
                su = Setup(side=trade_side, raid_bar=i, raid_level=lvl, raid_extreme=ext, structure_ref=ref)
                counters["raids"] += 1
                break

        if su is None:
            continue
        age = i - su.raid_bar
        if age > cfg["max_setup_bars"]:
            su = None; continue

        # -- 3. displacement
        if su.state == "RAIDED":
            if age > cfg["disp_window"]:
                su = None; continue
            body = abs(c[i] - o[i]); rng = h[i] - l[i]
            if cfg["disp"] == "V3":
                good = True
            elif cfg["disp"] == "V2":                                    # Qwen's numbers
                cp = (c[i] - l[i]) / rng if rng > 0 else 0.5
                good = (body >= 1.5 * A[i] and rng >= 1.0 * A[i] and
                        ((cp >= 0.70) if su.side > 0 else (cp <= 0.30)) and
                        ((c[i] > o[i]) if su.side > 0 else (c[i] < o[i])))
            else:                                                        # V1: range vs recent median, right way up
                good = (np.isfinite(med_rng[i]) and rng >= 1.5 * med_rng[i] and
                        ((c[i] > o[i]) if su.side > 0 else (c[i] < o[i])))
            if good:
                su.disp_bar = i; su.state = "DISPLACED"
                su.disp_lo = float(min(l[su.raid_bar:i + 1])); su.disp_hi = float(max(h[su.raid_bar:i + 1]))
                counters["displaced"] += 1
            else:
                continue

        # -- 4. MSS
        if su.state == "DISPLACED":
            if age > cfg["mss_window"]:
                su = None; continue
            if cfg["mss"] == "V2":                                       # Qwen: close beyond the structure ref
                done = (c[i] >= su.structure_ref) if su.side > 0 else (c[i] <= su.structure_ref)
            else:                                                        # V1 (book): structure taken by the leg
                done = (h[i] >= su.structure_ref) if su.side > 0 else (l[i] <= su.structure_ref)
            if done:
                su.mss_bar = i; su.state = "MSS_OK"; counters["mss"] += 1
            else:
                continue

        # -- 5. FVG (3-bar, uses i-2..i only), beyond the 50% of the displacement range on the liquidity side
        if su.state == "MSS_OK":
            if age > cfg["max_setup_bars"] or (su.mss_bar is not None and i - su.mss_bar > cfg["fvg_window"]):
                su = None; continue
            if i - su.raid_bar < 2:
                continue
            if su.side > 0:
                lo_g, hi_g = h[i - 2], l[i]
            else:
                lo_g, hi_g = h[i], l[i - 2]
            if not (hi_g - lo_g >= cfg["min_fvg_atr"] * A[i]):
                continue
            su.disp_lo = min(su.disp_lo, float(min(l[su.raid_bar:i + 1])))
            su.disp_hi = max(su.disp_hi, float(max(h[su.raid_bar:i + 1])))
            eq = 0.5 * (su.disp_lo + su.disp_hi)
            beyond = (lo_g <= eq) if su.side > 0 else (hi_g >= eq)       # FVG on the liquidity (discount/premium) side
            if not beyond:
                continue
            su.fvg_bar = i; su.fvg_lo, su.fvg_hi = float(lo_g), float(hi_g); su.state = "FVG_OK"
            counters["fvg"] += 1

            # -- 6. order
            if cfg["entry"] == "V2":
                limit = 0.5 * (lo_g + hi_g)                              # Qwen: FVG midpoint
            else:
                limit = float(np.clip(eq, lo_g, hi_g))                   # book: equilibrium, clipped into the FVG
            buf = cfg["stop_buf_atr"] * A[i]
            if cfg["stop"] == "V2":
                stop = su.raid_extreme - buf if su.side > 0 else su.raid_extreme + buf
            elif cfg["stop"] == "V3":
                adr = float(np.nanmean(med_rng[max(0, i - 100):i + 1])) * 5
                stop = su.raid_extreme - 0.5 * adr if su.side > 0 else su.raid_extreme + 0.5 * adr
            else:                                                        # V1 (Qwen): min(FVG bottom, raid extreme)
                base_lvl = min(lo_g, su.raid_extreme) if su.side > 0 else max(hi_g, su.raid_extreme)
                stop = base_lvl - buf if su.side > 0 else base_lvl + buf
            risk = abs(limit - stop)
            if risk <= 0 or risk > cfg["max_stop_atr"] * A[i]:
                su = None; continue
            tgt = None
            if cfg["tgt"] == "V1":
                bsl2, ssl2 = pools_at(i)
                arr = bsl2 if su.side > 0 else ssl2
                j = np.searchsorted(arr, limit, "right" if su.side > 0 else "left")
                cand = None
                if su.side > 0 and j < len(arr):
                    cand = float(arr[j])
                elif su.side < 0 and j > 0:
                    cand = float(arr[j - 1])
                if cand is not None:
                    rr = abs(cand - limit) / risk
                    if cfg["min_rr"] <= rr <= cfg["max_rr"]:
                        tgt = cand
            if tgt is None:
                tgt = limit + su.side * cfg["def_rr"] * risk
            order = dict(side=su.side, limit=limit, stop=stop, target=tgt, fill_from=i + 1,
                         expiry=i + cfg["order_ttl"], raid_bar=su.raid_bar,
                         invalid=(min(lo_g, su.raid_extreme) if su.side > 0 else max(hi_g, su.raid_extreme)))
            counters["orders"] += 1
            su.state = "ORDER"

    bl = pd.DataFrame(trades)
    if verbose:
        funnel = " -> ".join(f"{k} {v}" for k, v in counters.items())
        print(f"  {inst:<8}{pair:<8}{kz:<7} {funnel}", flush=True)
        if len(bl):
            R = bl.R.to_numpy(float)
            t = R.mean() / (R.std(ddof=1) / np.sqrt(len(R))) if len(R) > 2 else np.nan
            sel = (pd.to_datetime(bl.entry_time) < SEL_END).to_numpy()
            print(f"           n {len(R)}  meanR {R.mean():+.3f}  t {t:+.2f}  win {100*(R>0).mean():.1f}%  "
                  f"PF {R[R>0].sum()/max(-R[R<=0].sum(),1e-9):.2f}  "
                  f"2018-22 {R[sel].mean() if sel.any() else float('nan'):+.3f} / "
                  f"2023+ {R[~sel].mean() if (~sel).any() else float('nan'):+.3f}", flush=True)
    return bl, counters


if __name__ == "__main__":
    if sys.argv[1] == "summary":
        fs = sorted(OUT.glob("S1_*.csv"))
        d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()
        if not len(d):
            print("no trades yet"); sys.exit()
        g = d.groupby(["inst", "pair", "kz"]).R.agg(["size", "mean", "sum"])
        g["t"] = d.groupby(["inst", "pair", "kz"]).R.apply(
            lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan)
        print(g.round(3).sort_values("t", ascending=False).to_string())
        print(f"\ncells {len(g)}   cells with t >= 3.27: {int((g.t >= 3.27).sum())}   "
              f"positive: {int((g['mean'] > 0).sum())}   total trades {len(d)}")
    else:
        inst = sys.argv[1]
        base0, _, _ = MM.load(inst)
        base0 = base0.loc[:CAP]                      # load once; four cells share it
        for pair in PAIRS:
            for kz in KILLZONES:
                bl, _ = run_instrument(inst, pair, kz, base=base0)
                if len(bl):
                    bl.to_csv(OUT / f"S1_{inst}_{pair.replace('>', '-')}_{kz}.csv", index=False)
