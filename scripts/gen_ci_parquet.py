from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from ste.ingest.parquet_store import write_bars
from ste.ingest.synthetic import bars_from_closes_ohlc


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera Parquet sintético reproducible para CI gates.")
    ap.add_argument("--out", type=str, required=True, help="Ruta de salida .parquet")
    ap.add_argument("--n", type=int, default=180, help="Número de barras")
    ns = ap.parse_args()

    out = Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    drift = 0.00025
    noise = 0.0020 * rng.standard_normal(int(ns.n))
    rets = drift + noise
    closes = 100.0 * np.cumprod(1.0 + rets)
    bars = bars_from_closes_ohlc(
        closes.astype(np.float64),
        symbol="CI",
        timeframe="1d",
        t0=datetime(2020, 1, 1, tzinfo=timezone.utc),
        step=timedelta(days=1),
    )
    write_bars(out, bars, run_meta={"source": "ci_synth", "seed": 42})
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
