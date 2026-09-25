# Getting data in

One CSV per instrument, in this folder, named `<INSTRUMENT>.csv`:

```
timestamp,open,high,low,close,spread
2018-01-02 00:00:00,6534.1,6535.8,6533.9,6535.2,1.4
```

The instrument name is whatever you pass on the command line: `python ict_model.py USTEC` reads `data/USTEC.csv`.

## From MetaTrader 5 (the export the study used)

1. Tools -> Options -> Charts -> "Max bars in chart": set to Unlimited, restart the terminal.
2. Open the symbol on M1, scroll back to 2018 (hold Home) so the history is actually downloaded.
3. Tools -> History Center (F2) -> pick the symbol and M1 -> Export.
4. The export is tab-separated with `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>`.
   The loader tolerates the angle brackets, but you must fix two things yourself:

   - **Join `<DATE>` and `<TIME>` into one `timestamp` column.**
   - **`<SPREAD>` is in POINTS, not price.** Multiply by the symbol's point size. On a 2-digit gold feed that is
     `spread_price = spread_points * 0.01`; on a 5-digit EURUSD feed, `* 0.00001`. Getting this wrong by a factor
     of ten is the single easiest way to make this model look profitable.

   A further warning from the study: on several feeds `<SPREAD>` is a **posted tariff**, not a measured one - it
   sits at a constant value for years and tells you nothing about real liquidity. Check whether yours varies
   before you trust cost-sensitive results.

## Timezone

`KILLZONES` in `ict_model.py` is expressed in minutes from midnight **in the timestamp's own clock**:

```python
KILLZONES = {"LONDON": (2 * 60, 5 * 60), "NY": (7 * 60, 10 * 60)}
```

Those are New York hours (02:00-05:00 and 07:00-10:00 ET), because the study's feed was NY time. If your broker
is UTC+2/+3, either convert the timestamps to New York on export or change these numbers. A silently shifted
killzone is the most common way to fail to reproduce this.

## Bar size

Indices, metals and crypto were run on 1-minute bars; FX on 5-minute. Any resolution at or below the structure
rule (M5 or M15) is fine - the model resamples up internally.

## What the study used

12 instruments, 2018-01-01 to 2026-05-21: USTEC, US500, US30, US2000, XAUUSD, EURUSD, GBPUSD, USDJPY, USDCHF,
USDCAD, BTCUSD, ETHUSD. No data is included in this repo; it is not ours to redistribute.
