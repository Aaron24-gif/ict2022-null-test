# ICT 2022 MENTORSHIP MODEL — PRE-REGISTRATION
Written 2026-09-25, before any code was run. Source: *Unlocking Success in ICT 2022 Mentorship* (LumiTraders,
2023), 407pp, text extracted to `Downloads/ict2022_text.txt`. Page numbers below are PDF pages.

## 1. SOURCE RECONSTRUCTION — what the book actually specifies

**The model itself (p249-250), quoted structure:**
1. Price trades through major Buyside or Sellside Liquidity (Asian High/Low, London High/Low, Previous Day(s)
   High/Low, etc.).
2. Price reverses direction and creates a **Fair Value Gap with Displacement** — "Displacement must exist. This
   signifies there is Institutional sponsorship to the move."
3. A swing high/low **exactly horizontal to one of the three candles in the FVG** — that swing is the **Market
   Structure Shift**. "The Swing High/Low can occur either before the liquidity grab or afterwards. Either way is
   valid."
4. Draw a **50% Fibonacci** line, two options: (a) from the swing that took liquidity to a swing on the other side
   of the FVG; (b) from a prominent swing after liquidity.
5. The FVG gap "must be on the Equilibrium line (50%) or on the side of the Liquidity (i.e. the better side)".
6. **Place a limit order inside the FVG** at equilibrium or better.

Condensed restatement on the same page: liquidity grab → displacement → MSS → FVG/OB beyond the 50% of the
displacement range → return to FVG/OB → solid risk-reward.

**Displacement range (p250, explicit):** "The displacement low is the short-term low being broken, and the
displacement high is the old high. The range between these two points is called the displacement range."

**Killzones (p95, explicit clock):** London open 02:00-05:00, New York open 07:00-10:00, London close 10:00-12:00,
CBDR 14:00-20:00, Asia 20:00-00:00, all New York local time.

**Stops (p385 buy / p388 sell):** instrument-specific ES point counts — 15 pts under a sell-stop raid, 20 pts under
a run beneath the Asian range, 5 pts under LOD for a first retracement into an order block — with a catch-all of
"50% ADR of the last 5 days" from the Asian range. These are ES-denominated and discretionary.

**Targets (p388):** scale-outs — 10-15 ES points, every 2 SD of the Asian range/CBDR, previous day's low, 50% of
the 1h range, 60-80% at the 5-day ADR projection, plus time-of-day scale-outs at 05:00 and before 07:00.

## 2. WHERE THE SOURCE IS DISCRETIONARY — and the conservative reading taken
| # | Ambiguity | Reading used in VERSION A (source-faithful) | Named alternatives (VERSION B) |
|---|---|---|---|
| 1 | "major" liquidity | Asian high/low (20:00-00:00), London high/low (02:00-05:00), previous day high/low — the three the book names first | + previous week H/L, + equal highs/lows |
| 2 | "trades through" | any trade beyond the level by > 0 | RAID_V2: close beyond; RAID_V3: depth >= 2bp |
| 3 | "displacement" | the FVG-forming 3-bar sequence whose middle bar range >= 1.5x the median of the prior 20 bars AND which breaks the MSS swing | DISP_V2: body/range >= 0.6; DISP_V3: no displacement filter at all (tests whether it matters) |
| 4 | FVG | classic 3-candle gap: bar1.high < bar3.low (bullish) / bar1.low > bar3.high (bearish) | FVG_V2: include order block (last opposing candle before displacement) |
| 5 | "swing exactly horizontal to one of the three candles" | a confirmed 2-bar fractal whose price lies within the high-low span of any of the three FVG candles | MSS_V2: fractal broken by the displacement leg, ignoring the horizontal-alignment clause |
| 6 | 50% fib anchor | option (a): swing that took liquidity → swing on the other side of the FVG | FIB_V2: option (b), prominent swing after liquidity |
| 7 | "better side of equilibrium" | FVG must lie at or beyond the 50% of the displacement range, on the liquidity side | — |
| 8 | Entry | **limit at the FVG boundary nearest equilibrium** (the book says limit, so no market entry) | ENTRY_V2: limit at FVG 50%; ENTRY_V3: market on FVG touch |
| 9 | Stop | beyond the liquidity-raid extreme (the structural point the model is built on). The ES point counts are not portable across our 26 instruments | STOP_V2: 50% of 5-day ADR from the raid extreme (the book's catch-all) |
| 10 | Target | opposite liquidity pool (the "draw on liquidity"); reported alongside a fixed 2R reference | TGT_V2: 2R fixed; TGT_V3: previous day H/L |
| 11 | Timeframe | the book teaches this on 5m/15m with 1m entries (p103: "look for a FVG, BB, or OB on the 5/15m chart") | M15→M1 and M5→M1 in Stage 1; H1→M15 only if Stage 1 shows anything |
| 12 | Expiry | setup dies if the FVG is not touched within 120 structure bars (kept fixed so every arm of this study is comparable) | — |

**Not included** (the book covers them but they are not part of the 2022 model per p284, which lists 2022 Model,
OFED and Breaker+FVG as three *separate* entry models): MMXM, ATM method, Power of 3, intermarket analysis.

## 3. STAGE 1 — the frozen first run (no optimisation, no variant search)
VERSION A only, defaults above, on the 12 real-spread 1-minute instruments.
Cells: 2 structure pairs (M15→M1, M5→M1) × 2 stated killzones (London 02-05, NY 07-10) × 12 instruments = **48 cells.**
Bar: Sidak for 48 tests → alpha 0.00107 → **|t| >= 3.27**, and the cell must also be positive at 2x spread.
Reported: expectancy R, PF, total R, maxDD, trades/yr, MAE/MFE, win rate, per-year and split-half, cost share.

## 4. STAGE 2 — component decomposition (only what the architecture supports)
Run only if Stage 1 is not uniformly negative. Each component is tested as its own entry rule on the same
population so the contributions are additive-comparable:
A liquidity raid alone (enter on reclaim) · B raid + displacement · C raid + MSS · D raid + FVG ·
E MSS + FVG without a raid · F displacement alone · G the complete sequence (= Stage 1) ·
H complete sequence minus the horizontal-swing clause · I complete minus the equilibrium filter ·
J complete with entry at market instead of limit.
10 components × 12 instruments = 120 tests → **|t| >= 3.75**. The purpose is to find which clause carries
information, not to find a profitable cell.

## 5. CONTROLS (identical to the programme's standard)
direction flip · matched random-entry placebo (same window, same stop distribution, coin-flip direction, 300
resamples) · shifted-level placebo for the raid level (0.3-0.7 ATR) · split-half 2018-22 vs 2023+ · 1x/2x/3x cost ·
instrument transfer · window transfer across the 8-block grid as a diagnostic only.

## 6. DATA AND GUARDS
1-minute + real per-bar spread: XAUUSD, USTEC, US500, US30, US2000, BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, USDCAD,
USDCHF. 5-minute flat-cost set used only at Stage 3 transfer. **2018-01 → 2026-05-21 only. The sealed holdout
(2026-05-22 →) is not touched at any stage** and the loaders keep their hard cap.

## 7. WHAT WOULD MAKE THIS A RESULT
- **A** full model survives Stage 1 bar + controls → forward test (never straight to live).
- **B** a component survives while the full model does not → extract and research separately.
- **C** a component changes the expectancy of an existing independently-defined strategy → document as a filter.
  **No other strategy is mixed into this model during development** (
  combining them here would contaminate both).
- **D** nothing survives → record what failed and why, including which clause killed it.

## 8. HARD RULES
No rule is changed after seeing a result: a change creates VERSION_2 with the reason logged. No threshold is
searched beyond the one predeclared neighbour. Win rate and RR are descriptive only. Every own-bug found is logged
in RESULTS.md — this programme has had five self-inflicted false positives, three of them in the last two days,
so the leak checklist (level knowable-from time, cost applied to both directions, no future-confirmed pivots,
stop-first on same bar) is run **before** any positive number is reported.

---
# AMENDMENT 1 — 2026-09-25: cross-model diff (Qwen spec v1.0, ChatGPT notes) vs the book
Both models were asked for the rules independently. Where they disagree with the book, **the book wins** (the
user's rule). Where they disagree with each other, the clause becomes a named variant. Qwen's document is a full
deterministic spec and supplies numbers where the book is silent — those numbers are adopted as pre-declared
proxies rather than invented by me, which is strictly better for this programme.

| # | Clause | Book (p249-250, p95, p385/388) | Qwen v1.0 | Decision |
|---|---|---|---|---|
| 1 | Session windows | London 02:00-05:00, NY 07:00-10:00 **New York time** (p95) | London 07:00-10:00, NY 12:00-15:00 **fixed UTC** | **Book.** Qwen's fixed-UTC windows equal the book's only in US winter; they drift an hour every summer. Our engine is NY-local with DST, as the programme already requires. Qwen's DST bug is logged. |
| 2 | Liquidity raid | "Price trades through" the level, then reverses | requires the sweep bar to also **close back** through the level | **Both, named:** RAID_V1 (book: trade-through, reversal evidenced later by displacement) vs RAID_V2 (Qwen: same-bar close-back). |
| 3 | MSS | the swing "exactly horizontal to one of the three candles in the FVG" (p249) | close beyond a `structure_ref` = most recent opposing confirmed pivot before the sweep | **Both, named:** MSS_V1 (book, horizontal alignment) vs MSS_V2 (Qwen, close-through structure). **This is the largest divergence in the two specs and is the key decomposition clause.** |
| 4 | Displacement | "must exist … Institutional sponsorship" — no numbers | body >= 1.5 ATR, range >= 1.0 ATR, close in top/bottom 30% | **Qwen's numbers as DISP_V2**; my median-range proxy as DISP_V1; **DISP_V3 = no displacement filter** (tests whether the clause carries anything at all). |
| 5 | Entry | limit inside the FVG "at the Equilibrium or on the better side of Equilibrium" (equilibrium = 50% of the displacement range) | limit at the FVG **midpoint** (consequent encroachment) | **Both, named:** ENTRY_V1 (book: displacement-range 50%, clipped into the FVG) vs ENTRY_V2 (Qwen: FVG midpoint). |
| 6 | Stop | ES point counts (15/20/5) or 50% of 5-day ADR — not portable | min(FVG bottom, swept extreme) − 0.25 ATR | **Qwen's as STOP_V1** (portable and structural); raid extreme alone as STOP_V2; ADR catch-all as STOP_V3. |
| 7 | Target | scale-outs at many discretionary points (p388) | nearest opposing liquidity pool if RR in [1.5, 4.0], else 2R | **Qwen's as TGT_V1** (it operationalises the book's "draw on liquidity" + "solid RR"); fixed 2R as TGT_V2. |
| 8 | Risk engine | — | daily/weekly loss limits, cooldowns, consecutive-loss halts | **OFF for research.** These are account rules that change the trade population and would confound the edge measurement. They belong in a deployment layer, not a mechanism test. |
| 9 | Order life | — | TTL 10 bars, cancel on close beyond FVG/swept extreme, session-end cancel | **Adopted** (the book is silent; this is the conservative reading). |
| 10 | Pivots | — | strict inequality, 3-bar right lag | **Programme convention instead**: a 2-bar confirmed fractal, fixed in advance and used identically in every arm. Logged as a deviation from both specs. |

**ChatGPT's set** adds no numeric definitions beyond Qwen's and uses `>=` on the right side of a pivot (allowing
equal highs), which our fractal convention rejects. Its substantive contribution is the staging discipline
(literal model first, variants second) which this pre-registration already follows, and the warning that the 2022
model is a teaching framework with no independent evidence of edge — recorded as the prior.

## Stage 1 frozen spec (one configuration, no search)
RAID_V1 · DISP_V1 · MSS_V1 · FVG 3-bar with min size 0.20 ATR · ENTRY_V1 · STOP_V1 · TGT_V1 · book killzones ·
M15→M1 and M5→M1 · 12 real-spread instruments · 48 cells · bar |t| >= 3.27 · must hold at 2x spread.

## Stage 3 variant budget (fixed now, only runs if Stage 1 or 2 shows something)
Exactly 8 variants: RAID_V2, DISP_V2, DISP_V3, MSS_V2, ENTRY_V2, STOP_V2, STOP_V3, TGT_V2 — each changing ONE
clause from the Stage 1 spec. 8 variants x 12 instruments = 96 tests, bar |t| >= 3.46. No other combinations.

---

## AMENDMENT 2 — raid as CONTINUATION (registered 2026-09-25, before running)

**Why.** Stage 2 component A (raid, faded, market entry) returned −0.222R / −0.219R with t −35.2 / −36.4 on ~92,000
trades and a 25.9% win rate against a 33.3% null. An effect that large and that consistent is a statement about
direction: raids are followed, not faded. The book asserts the opposite. This tests the book's claim with its sign
reversed.

**What is NOT allowed.** The continuation result may not be inferred by negating the fade's R. Negating hands the
strategy two free spreads and a mirrored stop it never had to pay for — that is the T4 error in the registry. The
continuation must be traded as its own order, paying its own spread, with its own stop.

**Specification.** `flip=True` reverses the side at signal creation and mirrors the stop to the raid bar's opposite
extreme:
- buy-side raid (price trades through resting BSL): fade = short with the stop at the raid high;
  **continuation = long with the stop at the raid low**
- sell-side raid: fade = long, stop at the raid low; **continuation = short, stop at the raid high**
Everything else is unchanged: same pools, same killzones, same 2R target, same per-bar spread, same exit walk.
The 2R barrier-race null is 33.3% regardless of stop placement, so the comparison to the null remains valid even
though the continuation's R unit differs from the fade's.

**Arms (3 components × 12 instruments × 2 killzones × 2 structure rules):**
| component | entry | fill |
|---|---|---|
| `A_raid_cont` | market at next open | n/a |
| `FULL_cont` | limit into the FVG | touch |
| `FULL_cont_pess` | limit into the FVG | through (queue-realistic) |

`A_raid_cont` is the primary test — market entry, so no fill assumption can create the result.
`FULL_cont` / `FULL_cont_pess` ask the secondary question: does the rest of the sequence add anything once the
direction is corrected? They are reported as a pair; only the `_pess` number counts as a result.

**Bars (fixed now).** 3 pooled component comparisons -> Sidak alpha 0.0170 -> **pooled |t| >= 2.39**.
72 individual cells -> Sidak alpha 0.000713 -> **per-cell |t| >= 3.38**.

**Kill conditions, fixed in advance.**
1. `A_raid_cont` pooled |t| < 2.39 -> the asymmetry is not tradeable, only descriptive. Branch closes.
2. `A_raid_cont` pooled t >= 2.39 but the effect does not hold in BOTH halves (2018-22 and 2023+) -> closes.
3. Any positive result that is not also positive at 2x cost -> closes.
4. `FULL_cont` positive while `FULL_cont_pess` is not -> it is the fill again, not the direction. Closes.

**Prediction, on the record.** I expect `A_raid_cont` to come back positive but SMALLER than +0.222R and possibly
below the bar, because the fade's loss is partly the 2R geometry losing the barrier race rather than a directional
edge, and because the continuation pays its own spread. If it lands near +0.22R the asymmetry is real and
tradeable; if it lands near zero, the fade's −0.22R was mostly cost and geometry.
