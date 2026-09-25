# ICT 2022 MODEL — RESULTS

## STAGE 1 — the complete source-faithful sequence (48 cells, 22,139 trades, bar |t| >= 3.27)
raid -> displacement -> MSS -> FVG beyond equilibrium -> limit entry, book killzones, M15>M1 and M5>M1, 12 instruments.

| pooled | value |
|---|---|
| trades | 22,139 |
| R per trade | **+0.0017** |
| t | +0.18 |
| profit factor | 1.003 |
| win rate | **33.3%** (a 2R target's coin-flip value is 33.3%) |
| 2018-22 / 2023+ | +0.004 / −0.001 |
| cells with t >= 3.27 | **0** |
| positive cells | 23 of 48 (chance: 24) |
| cell t-stats | mean −0.026, sd 1.128 (noise: 0, 1.0) |

**The complete model lands exactly on the barrier-race null.** Not cost-killed — PF is 1.003 after spread — and not
an implementation failure: the funnel filters hard (Nasdaq London: 2,606 raids -> 480 FVGs -> 313 trades) and the
win rate sits on the theoretical value a random entry with the same geometry would produce.
Best cell ETHUSD M15>M1 London t 2.57 on 189 trades — the second-best of 48 random draws sits there.
By killzone: NY +0.025, London −0.028. By side: long +0.028, short −0.009.

## STAGE 2 — component decomposition (bar |t| >= 3.75), Nasdaq first
| component | London | NY | reading |
|---|---|---|---|
| A raid alone | **−0.222R, t −35.2** | **−0.219R, t −36.4** | 92k trades, win 25.9% vs the 33.3% null. See Amendment 2 below before reading a direction into this |
| B raid + displacement | −0.137 | −0.109 | displacement does not rescue it |
| C raid + MSS | −0.157 | −0.131 | nor does the structure break |
| F displacement alone | −0.120, t −11.7 | −0.075, t −8.2 | 41k trades; displacement alone is negative |
| D raid + FVG (limit) | +0.065 | +0.013 | the only arms that reach zero contain the FVG LIMIT |
| E MSS + FVG, no raid | +0.009 | +0.047 | the liquidity event contributes nothing |
| H full + the book's horizontal-swing clause | −0.134 | −0.034 | the book's own literal MSS test makes it WORSE |
| I full without the equilibrium filter | −0.067 | +0.078 | dropping a "required" clause does not hurt |
| J full, market entry instead of limit | −0.145 | −0.116 | same sequence, worse entry |

**D vs J is the decisive pair:** identical sequence, limit-into-the-gap vs market-at-next-open, 0.21R apart. What
lifts the model off the floor is the price improvement of waiting for a retracement, not the pattern.

## STAGE 2b — is the FVG a LOCATION, or just a limit order? (shifted-gap placebo)
Same machinery, but the gap is moved to a price that is not a gap (`shift=True`): the limit sits where no imbalance
exists. If the FVG were a real level, the placebo should die.

| pooled over 12 instruments | real gap | shifted (fake) gap |
|---|---|---|
| D raid + FVG limit | +0.032R, t +4.24, n 35,325 | **+0.049R** — the fake gap is BETTER |
| E MSS + FVG limit | +0.035R, t +4.50, n 33,712 | **+0.043R** — same |

**The FVG carries no information.** What the model is monetising is the limit order itself: buying a fixed distance
below the last price prints a small positive mean whether or not the level means anything. That is the well-known
bid-side fill premium, not an ICT mechanism.

## STAGE 2c — queue-realistic fills (the premium is not collectible)
The touch-fill assumption pays you every time price merely reaches your limit. Repriced so a passive order must
trade THROUGH the level (`need = spread`, fill worsened by a quarter spread — still generous, since it ignores
queue position and partial fills):

| pooled | touch fill | through fill | change |
|---|---|---|---|
| D raid + FVG limit | +0.0322R (t +4.24) | **−0.2099R (t −28.92)** | −0.2421 |
| E MSS + FVG limit | +0.0350R (t +4.50) | **−0.2008R (t −26.72)** | −0.2358 |

All 48 queue-realistic arms pooled: n 64,358, **−0.2055R, t −39.36**, win 26.5%.
**Positive arms: 2 of 48** — gold NY only, D +0.027 (t 0.85) and E +0.052 (t 1.53), both inside noise.
Every one of the other 11 instruments is negative in all four arms, London and NY, 2018-22 and 2023+.

The entire positive result in Stage 1 and Stage 2 was the difference between "price touched my limit" and
"my limit actually filled". Nothing survives the correction.

## STAGE 2d — portfolio view (what the Stage 1 winners are worth together)
| portfolio, every cell at equal risk per trade | CAGR | maxDD |
|---|---|---|
| HINDSIGHT — the 23 cells that came out positive | +89.4% | 56.4% |
| HONEST — all 48 cells, which is what you could have traded | **−26.8%** | **98.7%** |

Average pairwise correlation between the winning cells +0.02 — genuinely uncorrelated, which is exactly what
48 independent noise draws look like.

The hindsight number is unobtainable: it requires knowing in 2018 which 23 of the 48 cells would win. The honest
portfolio — the one you could actually have traded, because nothing told you in advance which cells those were —
loses money and draws down 98.7%.

A further check on the 23 winners, since "it improved my portfolio" is the usual defence: each was added to an
unrelated portfolio and the combination rescaled to the original's drawdown. Twelve of the 23 improved it. Then
the same test was run on 200 draws of ZERO-EDGE streams built from each cell's own trade dates and R magnitudes
with the mean subtracted. Those improve it 9.2 times out of 23 on average (95% range 5-14), so P(null >= 12) =
0.16. **Adding any uncorrelated stream and rescaling improves a portfolio about 40% of the time for free.**
Twelve of 23 is inside that.

## VERDICT — REJECT
The ICT 2022 model, built to the book's own specification with page-cited parameters and cross-checked against two
independent AI reconstructions, does not have an edge.

1. The complete model lands **exactly on the barrier-race null** (33.3% win rate at a 2R target, PF 1.003).
2. The decomposition shows **every named component is negative on its own** — the raid, the displacement, the MSS.
   Fading a raid loses −0.22R, t −35 on 92,000 trades - but so does following it (see Amendment 2).
3. The only positive arms are the ones containing a **limit order**, and a limit placed at a **fake** gap does
   just as well — so the FVG is not a location, it is an excuse to bid below the market.
4. That bid-side premium **does not survive an honest fill**: −0.21R, t −39 across 64,358 trades, 46 of 48 arms negative.
5. The profitable Stage 1 cells only combine into something if you are allowed to pick them **after** seeing the
   results. Traded honestly the same 48 cells lose money with a 98.7% drawdown.

No Stage 3 variant search is run: there is nothing to vary. The model's own components are the thing that fails.

**Branch CLOSED.** Reusable output kept: the raid-follow-through asymmetry (a raid is a continuation signal, not a
reversal one, on every instrument tested) and the touch-vs-through fill correction, which now applies to every
limit-entry test in the programme.

## AMENDMENT 2 — raid as CONTINUATION (the correction)

Component A showed that fading a liquidity raid loses 0.222R per trade with a t of −35 on 92,000 trades and a
25.9% win rate against a 33.3% null. The obvious inference is that raids are followed rather than faded.

That inference was pre-registered as a hypothesis and **traded**, not negated — negating a fade's R hands the
reversed trade two free spreads and a mirrored stop it never paid for. `flip=True` reverses the side at signal
creation and moves the stop to the raid bar's opposite extreme, so the continuation pays its own spread and its
own stop.

| raid, market entry, 2R target | per trade | t | win rate (null 33.3%) |
|---|---|---|---|
| faded | **−0.200R** | −181 | 26.7% |
| followed | **−0.150R** | −81 | 28.4% |

**Both directions lose, on every instrument tested.** Pre-registered kill condition 1 fires: the asymmetry is not
tradeable. It is not even directional — a win rate below the null on *both* sides means the shortfall comes from
the trade's geometry and its cost, not from which way it points. A 2R target with a stop just beyond the raid
extreme is reached less than a third of the time either way.

**Standing lesson, now in the programme's diagnostics: a losing result does not tell you the other side wins.**
To claim the reverse, trade the reverse.
