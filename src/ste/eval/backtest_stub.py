"""
Stub de *backtest* acoplado a *walk-forward*: rellenar con VectorBT / motor propio.

Sólo demuestra el *wiring* (ventanas → métricas vacías); no sustituye *VectorBT*.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ste.eval.metrics import max_drawdown, sharpe_ratio
from ste.eval.walkforward import iter_rolling


def run_walkforward_metrics_stub(returns: np.ndarray, train: int, test: int, step: int) -> list[dict[str, Any]]:
    n = int(returns.size)
    out: list[dict[str, Any]] = []
    for w in iter_rolling(n, train, test, step):
        r_test = returns[w.test[0] : w.test[1]]
        if r_test.size < 1:
            continue
        out.append(
            {
                "window": w,
                "sharpe": sharpe_ratio(r_test),
                "max_dd": max_drawdown(r_test),
                "train_len": w.train[1] - w.train[0],
                "test_len": w.test[1] - w.test[0],
            }
        )
    return out
