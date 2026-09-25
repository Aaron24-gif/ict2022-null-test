# The ICT 2022 model, tested against its own null

This repository contains a complete, runnable implementation of the ICT 2022 mentorship model, the pre-registration
that fixed the rules before the tests were run, and the results.

**The model does not have an edge.** 22,139 trades, 12 instruments, 2018–2026. It lands on the arithmetic value a
random entry with the same geometry would produce. Everything here is published so you can check that claim
instead of taking it.

The interesting part is not the verdict. It is the three controls that produced it, which are reusable on any
strategy, and which almost nobody runs.

---

## What was tested

The full sequence, built from the source material with page citations (see `PREREG.md`):

```
liquidity raid -> displacement -> market structure shift -> FVG beyond equilibrium -> limit entry -> 2R
```

Killzones as specified (London 02:00–05:00 ET, NY 07:00–10:00 ET), structure on M5 and M15 with entries on M1,
stops beyond the raid extreme, per-bar spread charged on entry and exit.

12 instruments: USTEC, US500, US30, US2000, XAUUSD, EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, BTCUSD, ETHUSD.

Two independent reconstructions of the spec (by two different language models) were diffed against each other
before any test ran; the five places they disagreed are recorded in `PREREG.md` as named ambiguities, with the
choice made and the reason. That is there so nobody has to argue about whether it was "implemented wrong".

## The result

| pooled over 48 cells | value |
|---|---|
| trades | 22,139 |
| R per trade | **+0.0017** |
| t | +0.18 |
| profit factor | 1.003 |
| win rate | **33.3%** |
| cells clearing the pre-registered bar | **0 of 48** |
| positive cells | 23 of 48 (chance expects 24) |

**33.3% is the null.** A strategy that risks 1 to make 2, entering at random, wins 1/(1+2) = 33.3% of the time.
The model matched it to three digits. It is not cost-killed — profit factor is 1.003 *after* spread. The funnel
also works: on Nasdaq London, 2,606 raids filter to 480 FVGs to 313 trades. It filters hard, and filters to noise.

---

## The three controls worth stealing

### 1. Know your null before you look at the P&L

Any fixed reward:risk with a hard stop is a barrier race. At a `k`R target the coin-flip win rate is `1/(1+k)` —
33.3% at 2R, 50% at 1R, 25% at 3R. Quote a win rate without quoting its null and the number means nothing.
A "56% win rate" is spectacular at 2R and catastrophic at 1R.

### 2. Move the level. If it still works, the level was never the point.

The only component arms that came out positive were the ones containing a limit order inside the fair value gap.
So the gap was moved 0.3–0.7 ATR away, at random, to a price where no imbalance exists — everything else
identical, same trigger times, same gap size, same stop geometry (`D_placebo`, `E_placebo`, the `shift=True` flag):

| pooled, 12 instruments | real gap | **fake** gap |
|---|---|---|
| raid + FVG limit | +0.032R | **+0.049R** |
| MSS + FVG limit | +0.035R | **+0.043R** |

The fake gap did better. The FVG is not a location — it is an excuse to place a limit order below the market.
Whatever the arm earned, it earned from bidding into a pullback, and the imbalance contributed nothing.

### 3. Touch is not a fill

Nearly every backtester fills a limit order the moment price *touches* it. That assumes you were first in the
queue and never adversely selected, and it is the single largest source of fake edge in retail backtests.
The `pess=True` flag requires price to trade *through* the limit by one spread and charges a quarter spread of
slippage — still generous, since it ignores queue position and partial fills:

| pooled | touch fill | through fill |
|---|---|---|
| raid + FVG limit | +0.0322R (t +4.24) | **−0.2099R (t −28.92)** |
| MSS + FVG limit | +0.0350R (t +4.50) | **−0.2008R (t −26.72)** |

All 48 arms: **−0.2055R, t −39.4** on 64,358 trades. 46 of 48 negative.
The fill assumption was worth **+0.24R per trade** — and it was producing the entire positive result.

---

## The part that is not a null result

The decomposition runs each clause of the model alone. Every one is negative, but one is enormous:

| component | London | NY |
|---|---|---|
| **raid alone, faded** | **−0.222R, t −35.2** | **−0.219R, t −36.4** |
| raid + displacement | −0.137 | −0.109 |
| raid + MSS | −0.157 | −0.131 |
| displacement alone | −0.120 | −0.075 |
| full model, market entry instead of limit | −0.145 | −0.116 |

92,000 trades at a 25.9% win rate against a 33.3% null. **Liquidity raids are followed, not faded**, on every
instrument tested, in both halves of the sample. The book's central directional claim is backwards, and the
effect is one of the largest in the study — pointing the wrong way.

Whether the reverse is *tradeable* is a separate question with its own pre-registration (`PREREG.md`,
Amendment 2), because a fade's loss is not automatically a continuation's profit: negating the R would hand the
reversed trade two free spreads and a stop it never paid for. It has to be traded to be claimed.

---

## Running it

```bash
pip install -r requirements.txt
# put your own CSVs in data/ — see data/HOWTO.md
python ict_model.py USTEC          # Stage 1: the complete model
python ict_model.py summary        # pooled Stage 1 table
python ict_components.py USTEC     # Stage 2: every component, both placebos, both fill models
python ict_components.py summary   # pooled Stage 2 table
python ict_components.py XAUUSD D_placebo,D_pess    # or pick specific arms
```

Components live in the `COMPONENTS` dict at the top of `ict_components.py`; each is a set of switches over one
engine, so no arm can differ from another by an accident of implementation.

No data is included — it is not ours to redistribute. `data/HOWTO.md` has an MT5 export recipe and the two
mistakes that will otherwise silently break your reproduction (spread in points vs price, and killzone timezone).

## Files

| file | what it is |
|---|---|
| `PREREG.md` | the rules, fixed before running: spec with page cites, 12 named ambiguities, significance bars, kill conditions |
| `RESULTS.md` | every result, including the ones that looked good before the controls |
| `ict_model.py` | Stage 1 — the complete model as a state machine |
| `ict_components.py` | Stage 2 — decomposition, placebos, fill models |
| `data.py` | the CSV seam |

## Honesty notes

- The significance bars and kill conditions in `PREREG.md` were written **before** the tests ran. That is the
  whole point of the file, and it is the only reason "0 of 48 cleared the bar" means anything.
- Five false positives were found and killed **in this programme's own code** before publication, each caused by
  a bug rather than by the market. They are logged rather than quietly fixed.
- One sealed out-of-sample period exists and was never loaded. It is not spent on a model that fails in-sample.
- This is research code. It is published because the model does not work; it is not a trading system, and
  nothing here is advice.
