from __future__ import annotations

import numpy as np

"""
Exponente de Hurst aproximado (heurística, solo NumPy).

Implementación estilo *varianza de incrementos* vs *lag* con regresión log-log; es
un indicador de *régimen* para gating, no un estimador MLE. Calibrar umbrales
con tu serie y frecuencia reales.
"""


def rough_hurst(series: np.ndarray) -> float:
    """
    Estimación de H: regresión entre log(lag) y log(std( X[t] - X[t-lag] )).

    Típico: series cerca de random walk retornan valores en torno a ~0.4–0.6
    (depende de preprocesado). Usar con ventana fija y comparar solo
    relativamente, no en absoluto entre activos distintos sin calibrar.
    """
    x = np.asarray(series, dtype=np.float64).ravel()
    if x.size < 32:
        return float("nan")
    x = x - float(np.mean(x))
    n = int(x.size)
    lags = range(2, min(100, n // 2))
    tau: list[float] = []
    lag_list: list[int] = []
    for lag in lags:
        diff = x[lag:] - x[:-lag]
        if diff.size < 1:
            continue
        s = float(np.std(diff, ddof=0))
        if s > 0.0 and np.isfinite(s):
            lag_list.append(lag)
            tau.append(s)
    if len(lag_list) < 4:
        return float("nan")
    lx = np.log(np.asarray(lag_list, dtype=np.float64))
    ly = np.log(np.asarray(tau, dtype=np.float64))
    a, b = np.polyfit(lx, ly, 1)
    h = float(a * 2.0)  # convención frecuente en snippets de varianza por lag
    return float(_clip_01ish(h))


def _clip_01ish(h: float) -> float:
    if not (h == h):
        return float("nan")
    return min(0.99, max(0.01, h))


def regime_gating_from_hurst(
    h: float,
    h_min_trade: float = 0.40,
    h_max_trade: float = 0.60,
) -> str:
    """
    Etiqueta tonta-v1: "ok" si H cae en una banda central; "avoid" si no, o si nan.

    Bandas estrechas = menos días "ok" (más defensivo). Ajusta a tu riesgo.
    """
    if h != h:
        return "avoid"
    if h < h_min_trade or h > h_max_trade:
        return "avoid"
    return "ok"
