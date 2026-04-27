from __future__ import annotations

import numpy as np

"""
Métricas básicas sobre *returns* 1D (frecuencia fija, sin costes; extender luego
con *turnover* y *slip* reales en la capa de *eval* completa).
"""


def _to_1d(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64).ravel()
    if a.size < 1:
        raise ValueError("necesita al menos un retorno")
    return a


def mean_excess(returns: np.ndarray, risk_free: float = 0.0) -> float:
    r = _to_1d(returns) - float(risk_free)
    return float(np.mean(r))


def volatility(returns: np.ndarray) -> float:
    r = _to_1d(returns)
    if r.size < 2:
        return 0.0
    return float(np.std(r, ddof=1, dtype=np.float64))


def sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0, ann_factor: float = 252.0) -> float:
    r = _to_1d(returns) - float(risk_free) / 252.0
    s = float(np.std(r, ddof=1)) if r.size > 1 else 0.0
    if s < 1e-16 or not np.isfinite(s):
        return 0.0
    m = float(np.mean(r)) * float(ann_factor) ** 0.5
    return m / s


def sortino_ratio(returns: np.ndarray, target: float = 0.0, ann_factor: float = 252.0) -> float:
    r = _to_1d(returns) - target
    downside = r.copy()
    downside[downside > 0.0] = 0.0
    d = float(np.sqrt(np.sum(downside**2) / max(1, downside.size - 1)))
    if d < 1e-16 or not np.isfinite(d):
        return 0.0
    m = float(np.mean(r)) * float(ann_factor) ** 0.5
    return m / d


def max_drawdown(returns: np.ndarray) -> float:
    r = _to_1d(returns)
    curve = np.cumprod(1.0 + r, dtype=np.float64)
    if curve.size < 1:
        return 0.0
    run_max = np.maximum.accumulate(curve)
    drawdown = 1.0 - curve / (run_max + 1e-16)
    return float(np.max(drawdown))
