"""
ICT 2022 -- STAGE 2 component decomposition (PREREG.md section 4; 10 components x 12 instruments, bar |t| >= 3.75).

The Stage 1 sequence is raid -> displacement -> MSS -> FVG(beyond equilibrium) -> limit entry. Stage 1 landed on
the exact barrier-race null (33.3% win at 2R). Stage 2 asks which clause, if any, carries information, by running
each clause on the same tape with everything else switched off.

  A raid alone                  enter next bar after the raid, stop beyond the raid extreme, 2R
  B raid + displacement         enter after the displacement bar
  C raid + MSS                  enter after the structure break
  D raid + FVG                  limit in the FVG, no displacement or MSS required
  E MSS + FVG, no raid          the sequence without the liquidity event
  F displacement alone          enter after any qualifying displacement in the killzone
  G complete (= Stage 1)        read from the Stage 1 files, not re-run
  H complete + horizontal clause the book's literal MSS test: the broken swing must sit inside one of the three
                                 FVG candles' price span. Stage 1 did NOT enforce this.
  I complete - equilibrium      drop "FVG must be beyond the 50% of the displacement range"
  J complete, market entry      enter at the next open instead of a limit inside the FVG

Usage: python ict_components.py <INSTRUMENT> | summary
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as MM                                        # noqa: E402
from ict_model import atr, fractals, build_levels, KILLZONES, CAP, SEL_END, OUT, STAGE1   # noqa: E402

COMPONENTS = {
    "A_raid":        dict(raid=True, disp=False, mss=False, fvg=False, entry="market"),
    "B_raid_disp":   dict(raid=True, disp=True,  mss=False, fvg=False, entry="market"),
    "C_raid_mss":    dict(raid=True, disp=False, mss=True,  fvg=False, entry="market"),
    "D_raid_fvg":    dict(raid=True, disp=False, mss=False, fvg=True,  entry="limit"),
    "E_mss_fvg":     dict(raid=False, disp=False, mss=True, fvg=True,  entry="limit"),
    "F_disp":        dict(raid=False, disp=True, mss=False, fvg=False, entry="market"),
    "H_horizontal":  dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit", horizontal=True),
    "I_no_equilib":  dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit", equilibrium=False),
    "J_market":      dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="market"),
    # -- controls for the one thing that cleared the pooled bar: is the +0.03R the GAP, or just the limit order?
    # identical logic, identical trigger times, identical gap size and stop geometry -- the gap is simply moved
    # 0.3-0.7 ATR away (random sign, fixed seed). If the placebo earns the same, the location carries nothing.
    "D_placebo":     dict(raid=True, disp=False, mss=False, fvg=True,  entry="limit", shift=True),
    # -- queue-realistic fills: our engine fills a limit the instant price TOUCHES it, which assumes you are first
    # in the queue and never adversely selected. These arms require price to trade THROUGH the limit by one spread
    # before filling, and charge a quarter-spread of slippage. If the +0.03R survives, it is real; if not, it was
    # the fill assumption.
    "D_pess":        dict(raid=True, disp=False, mss=False, fvg=True,  entry="limit", pess=True),
    "E_pess":        dict(raid=False, disp=False, mss=True, fvg=True,  entry="limit", pess=True),
    "E_placebo":     dict(raid=False, disp=False, mss=True, fvg=True,  entry="limit", shift=True),
    # -- the COMPLETE Stage-1 model, repriced. Every Stage-1 cell filled on a TOUCH; these two arms rerun the
    # full sequence with touch (FULL) and through (FULL_pess) fills, so the correction is measured on the
    # model itself instead of inferred from the D/E components.
    "FULL":          dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit"),
    "FULL_pess":     dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit", pess=True),
    # -- RAID AS CONTINUATION. Component A showed fading a raid loses 0.22R with t -35 on 92k trades, i.e. raids
    # are FOLLOWED. That is a claim about direction, so it has to be traded, not inferred by negating the fade
    # (negating hands you two free spreads - the T4 mistake). These arms reverse the side AT SIGNAL TIME and
    # mirror the stop to the raid bar's opposite extreme, so the trade pays its own spread and its own stop.
    "A_raid_cont":   dict(raid=True, disp=False, mss=False, fvg=False, entry="market", flip=True),
    "FULL_cont":     dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit",  flip=True),
    "FULL_cont_pess":dict(raid=True, disp=True,  mss=True,  fvg=True,  entry="limit",  flip=True, pess=True),
}
PAIR = os.environ.get("ICT_PAIR", "M5>M1")        # Stage 1 ran both structure rules
RULE = {"M5>M1": "5min", "M15>M1": "15min"}[PAIR]
tt = lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def walk_exit(o, h, l, c, sp, j, side, fill, stop, tgt, unit, cap=500):
    for x in range(j, min(len(h), j + cap)):
        if side > 0:
            hit_sl, hit_tp = l[x] <= stop, h[x] >= tgt
        else:
            hit_sl, hit_tp = h[x] + sp[x] >= stop, l[x] + sp[x] <= tgt
        if hit_sl:
            px = min(stop, o[x]) if side > 0 else max(stop, o[x] + sp[x])
            return side * (px - fill) / unit, "STOP", x
        if hit_tp:
            return side * (tgt - fill) / unit, "TP", x
    x = min(len(h), j + cap) - 1
    px = c[x] + (0.0 if side > 0 else sp[x])
    return side * (px - fill) / unit, "TIMEOUT", x


def make_sb(base):
    """Resample to the structure timeframe and hand back ONLY that. The 1-minute frame is ~250MB and is not used
    after this point; holding both is what pushed the box past its commit limit."""
    sb = base.resample(RULE, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "spread": "max"}).dropna()
    return sb.astype({c: "float32" for c in ("open", "high", "low", "close", "spread")})


def run(inst, kz="NY", base=None, cfg_extra=None, comp="G", verbose=True, sb=None):
    cfg = dict(STAGE1, **(cfg_extra or {}))
    C = COMPONENTS.get(comp, {})
    need_raid = C.get("raid", True); need_disp = C.get("disp", True)
    need_mss = C.get("mss", True); need_fvg = C.get("fvg", True)
    entry_mode = C.get("entry", "limit"); horizontal = C.get("horizontal", False)
    equilibrium = C.get("equilibrium", True); shift_on = C.get("shift", False); pess = C.get("pess", False); flip = C.get("flip", False)
    rng_p = np.random.default_rng(abs(hash(inst)) % (2 ** 32))
    if sb is None:
        if base is None:
            base, _, _ = MM.load(inst); base = base.loc[:CAP]
        sb = make_sb(base)
    o, h, l, c, sp = (sb[k].to_numpy(float) for k in ("open", "high", "low", "close", "spread"))
    idx = sb.index; A = atr(h, l, c)
    med = pd.Series(h - l).rolling(20).median().to_numpy()
    mins = np.asarray(idx.hour * 60 + idx.minute)
    k = cfg["pivot_lag"]
    pools = build_levels(idx, h, l, k)
    p_kn = np.array([x[0] for x in pools]); p_px = np.array([x[1] for x in pools]); p_sd = np.array([x[2] for x in pools])
    fh, fl = fractals(h, l, k)
    hi_i = np.array([i for i, _ in fh]); hi_p = np.array([p for _, p in fh])
    lo_i = np.array([i for i, _ in fl]); lo_p = np.array([p for _, p in fl])
    cache = {"at": -10 ** 9, "bsl": np.empty(0), "ssl": np.empty(0)}
    z0, z1 = KILLZONES[kz]
    trades = []

    def pools_at(i):
        if i - cache["at"] >= 256:
            m = (p_kn <= i - 1) & (i - p_kn <= 1000)
            cache["bsl"] = np.sort(p_px[m & (p_sd == +1)]); cache["ssl"] = np.sort(p_px[m & (p_sd == -1)])
            cache["at"] = i
        return cache["bsl"], cache["ssl"]

    def take(side, i, stop_lvl, limit=None, fvg=None):
        """Create the order and resolve it. Market = next open; limit = inside the FVG, TTL from cfg."""
        if entry_mode == "market":
            j = i + 1
            if j >= len(sb):
                return
            fill = o[j] + (sp[j] if side > 0 else 0.0)
            stop = stop_lvl - cfg["stop_buf_atr"] * A[i] * side
            unit = abs(fill - stop)
            if unit <= 2 * sp[j] or unit > cfg["max_stop_atr"] * A[i]:
                return
            tgt = fill + side * cfg["def_rr"] * unit
            R, why, x = walk_exit(o, h, l, c, sp, j, side, fill, stop, tgt, unit)
            trades.append(dict(inst=inst, comp=comp, kz=kz, side=side, entry_time=idx[j], exit_time=idx[x],
                               R=R, reason=why, unit=unit))
        else:
            stop = stop_lvl - cfg["stop_buf_atr"] * A[i] * side
            for j in range(i + 1, min(len(sb), i + 1 + cfg["order_ttl"])):
                need = sp[j] if pess else 0.0                      # must trade THROUGH the level, not just touch
                hit = (l[j] <= limit - need) if side > 0 else (h[j] + sp[j] >= limit + need)
                if hit:
                    fill = min(limit, o[j]) if side > 0 else max(limit, o[j] + sp[j])
                    if pess:
                        fill += 0.25 * sp[j] * side                 # adverse slippage on the fill
                    unit = abs(fill - stop)
                    if unit <= 2 * sp[j] or unit > cfg["max_stop_atr"] * A[i]:
                        return
                    tgt = fill + side * cfg["def_rr"] * unit
                    R, why, x = walk_exit(o, h, l, c, sp, j, side, fill, stop, tgt, unit)
                    trades.append(dict(inst=inst, comp=comp, kz=kz, side=side, entry_time=idx[j], exit_time=idx[x],
                                       R=R, reason=why, unit=unit))
                    return
                if (side > 0 and c[j] < fvg[0]) or (side < 0 and c[j] > fvg[1]):
                    return

    state = None
    for i in range(30, len(sb) - 2):
        if not np.isfinite(A[i]) or A[i] <= 0 or not (z0 <= mins[i] < z1):
            state = None; continue
        rng = h[i] - l[i]
        up = c[i] > o[i]
        disp_ok = np.isfinite(med[i]) and rng >= 1.5 * med[i]

        # -- setup creation
        if state is None:
            if need_raid:
                bsl, ssl = pools_at(i)
                a = np.searchsorted(bsl, c[i - 1], "right"); b = np.searchsorted(bsl, h[i], "right")
                if b > a:
                    state = dict(side=-1, bar=i, ext=h[i], lvl=float(bsl[a]))
                else:
                    a2 = np.searchsorted(ssl, l[i], "left"); b2 = np.searchsorted(ssl, c[i - 1], "left")
                    if b2 > a2:
                        state = dict(side=+1, bar=i, ext=l[i], lvl=float(ssl[b2 - 1]))
                if state is not None and flip:            # trade the follow-through, not the reversal
                    state = dict(side=-state["side"], bar=i, lvl=state["lvl"],
                                 ext=(l[i] if state["side"] < 0 else h[i]))
            elif need_disp and disp_ok:
                state = dict(side=(+1 if up else -1), bar=i, ext=(l[i] if up else h[i]), lvl=np.nan)
            elif need_mss:
                pr_h = hi_p[hi_i + k < i]; pr_l = lo_p[lo_i + k < i]
                if len(pr_h) and h[i] >= pr_h[-1]:
                    state = dict(side=+1, bar=i, ext=l[i], lvl=np.nan, mss=True)
                elif len(pr_l) and l[i] <= pr_l[-1]:
                    state = dict(side=-1, bar=i, ext=h[i], lvl=np.nan, mss=True)
            if state is None:
                continue
            state.setdefault("disp", False); state.setdefault("mss", False); state.setdefault("dlo", l[i])
            state.setdefault("dhi", h[i])
            if not need_disp and not need_mss and not need_fvg:            # component A / F: act immediately
                take(state["side"], i, state["ext"]); state = None
                continue
            if need_disp and not need_raid:
                state["disp"] = True
                if not need_mss and not need_fvg:      # component F: displacement alone, act now
                    take(state["side"], i, state["ext"]); state = None
                    continue
            continue

        age = i - state["bar"]
        if age > cfg["max_setup_bars"]:
            state = None; continue
        side = state["side"]
        state["dlo"] = min(state["dlo"], l[i]); state["dhi"] = max(state["dhi"], h[i])

        if need_disp and not state["disp"]:
            if age > cfg["disp_window"]:
                state = None; continue
            if disp_ok and ((up and side > 0) or (not up and side < 0)):
                state["disp"] = True
                if not need_mss and not need_fvg:
                    take(side, i, state["ext"]); state = None
                    continue
            else:
                continue

        if need_mss and not state["mss"]:
            if age > cfg["mss_window"]:
                state = None; continue
            pr_h = hi_p[hi_i + k < state["bar"]]; pr_l = lo_p[lo_i + k < state["bar"]]
            ref = (pr_h[-1] if len(pr_h) else np.nan) if side > 0 else (pr_l[-1] if len(pr_l) else np.nan)
            if not np.isfinite(ref):
                state = None; continue
            broke = (h[i] >= ref) if side > 0 else (l[i] <= ref)
            if broke:
                state["mss"] = True; state["ref"] = float(ref)
                if not need_fvg:
                    take(side, i, state["ext"]); state = None
                    continue
            else:
                continue

        if need_fvg:
            if i - state["bar"] < 2:
                continue
            lo_g, hi_g = (h[i - 2], l[i]) if side > 0 else (h[i], l[i - 2])
            if not (hi_g - lo_g >= cfg["min_fvg_atr"] * A[i]):
                continue
            if shift_on:                                    # move the gap, keep everything else
                off = (0.3 + 0.4 * rng_p.random()) * A[i] * (1 if rng_p.random() < 0.5 else -1)
                lo_g += off; hi_g += off
            eq = 0.5 * (state["dlo"] + state["dhi"])
            if equilibrium and not ((lo_g <= eq) if side > 0 else (hi_g >= eq)):
                continue
            if horizontal:                                                  # the book's literal MSS clause
                ref = state.get("ref", np.nan)
                span_lo = min(l[i - 2], l[i - 1], l[i]); span_hi = max(h[i - 2], h[i - 1], h[i])
                if not (np.isfinite(ref) and span_lo <= ref <= span_hi):
                    continue
            limit = float(np.clip(eq, lo_g, hi_g)) if equilibrium else 0.5 * (lo_g + hi_g)
            stop_lvl = min(lo_g, state["ext"]) if side > 0 else max(hi_g, state["ext"])
            take(side, i, stop_lvl, limit=limit, fvg=(lo_g, hi_g))
            state = None

    bl = pd.DataFrame(trades)
    if verbose and len(bl):
        R = bl.R.to_numpy(float); sel = (pd.to_datetime(bl.entry_time) < SEL_END).to_numpy()
        print(f"  {inst:<8}{comp:<15}{kz:<4} n {len(R):>5}  meanR {R.mean():>+7.3f}  t {tt(R):>+6.2f}  "
              f"win {100*(R>0).mean():>5.1f}%  2018-22 {R[sel].mean() if sel.any() else np.nan:+.3f} / "
              f"2023+ {R[~sel].mean() if (~sel).any() else np.nan:+.3f}", flush=True)
    elif verbose:
        print(f"  {inst:<8}{comp:<15}{kz:<4} no trades", flush=True)
    return bl


if __name__ == "__main__":
    if sys.argv[1] == "summary":
        fs = sorted(OUT.glob("S2_*.csv"))
        d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
        g = d.groupby("comp").R.agg(["size", "mean"])
        g["t"] = d.groupby("comp").R.apply(lambda x: tt(x.to_numpy(float)))
        g["win%"] = d.groupby("comp").R.apply(lambda x: 100 * (x > 0).mean())
        print("POOLED BY COMPONENT (all instruments, both killzones)")
        print(g.round(3).sort_values("t", ascending=False).to_string())
        pc = d.groupby(["comp", "inst"]).R.apply(lambda x: tt(x.to_numpy(float)) if len(x) > 20 else np.nan).dropna()
        print(f"\ncells {len(pc)}   with t >= 3.75: {int((pc >= 3.75).sum())}   positive: {int((pc > 0).sum())}")
        print("\ntop cells:"); print(pc.sort_values(ascending=False).head(8).round(2).to_string())
    else:
        inst = sys.argv[1]
        t0 = time.time()
        base0, _, _ = MM.load(inst)
        sb0 = make_sb(base0.loc[:CAP])
        del base0                                     # free the 1-minute frame before the loop
        comps = sys.argv[2].split(",") if len(sys.argv) > 2 else list(COMPONENTS)
        for comp in comps:
            for kz in KILLZONES:
                bl = run(inst, kz, sb=sb0, comp=comp)
                if len(bl):
                    tag = f"_{PAIR.replace(chr(62), chr(45))}" if comp.startswith(("FULL", "A_raid_cont")) else ""
                    bl.to_csv(OUT / f"S2_{inst}_{comp}{tag}_{kz}.csv", index=False)
        print(f"{inst} done ({time.time()-t0:.0f}s)", flush=True)
