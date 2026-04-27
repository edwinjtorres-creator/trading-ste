from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ste.eval.backtest_stub import run_walkforward_metrics_stub
from ste.eval.walkforward import walk_window_to_dict
from ste.ingest.parquet_store import read_bars


def bars_to_log_returns(bars: list) -> np.ndarray:
    """
    Retornos logarítmicos alineados a cierres consecutivos; longitud n-1 para n bares.
    """
    c = np.array([b.close for b in bars], dtype=np.float64)
    if c.size < 2:
        return np.array([], dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.diff(np.log(c))
    r = np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0)
    return r.astype(np.float64)


def walkforward_report_from_parquet(
    path: str | Path,
    train: int,
    test: int,
    step: int,
) -> list[dict[str, Any]]:
    """
    Lee *Parquet* de bares, ordena por tiempo, retornos log y *walk-forward stub*.
    """
    p = Path(path)
    bars = read_bars(p)
    if not bars:
        return []
    bars = sorted(bars, key=lambda b: b.open_time_utc)
    rets = bars_to_log_returns(bars)
    if rets.size < train + test:
        return []
    raw = run_walkforward_metrics_stub(rets, train, test, step)
    out: list[dict[str, Any]] = []
    for row in raw:
        w = row["window"]
        d = {k: v for k, v in row.items() if k != "window"}
        d["window"] = walk_window_to_dict(w)
        out.append(d)
    return out
