from __future__ import annotations

import numpy as np

Signal = int  # -1 short / flat, 0 neutral, 1 long / risk-on


def momentum_signal(closes: np.ndarray, fast: int = 10, slow: int = 30) -> np.ndarray:
    """
    Señal discreta simple: cruce de medias sobre precios de cierre.

    Útil como *baseline* reproducible (no promete alpha); sirve para cablear
    riesgo, pruebas y orquestación antes de modelos más complejos.

    Parameters
    ----------
    closes
        Precios de cierre, 1D, al menos `slow` puntos.
    fast, slow
        Ventanas (slow > fast >= 1).
    """
    c = np.asarray(closes, dtype=np.float64).ravel()
    if c.size < slow:
        raise ValueError("closes debe tener al menos 'slow' observaciones")
    if slow <= fast:
        raise ValueError("slow debe ser mayor que fast")

    w_fast = 1.0 / fast
    w_slow = 1.0 / slow
    # EMAs estables sin pandas
    ema_f = _ema(c, w_fast)
    ema_s = _ema(c, w_slow)
    diff = ema_f - ema_s
    out = np.zeros(c.shape[0], dtype=np.int8)
    out[diff > 0] = 1
    out[diff < 0] = -1
    return out


def _ema(x: np.ndarray, alpha: float) -> np.ndarray:
    y = np.empty_like(x)
    y[0] = x[0]
    for i in range(1, x.size):
        y[i] = alpha * x[i] + (1.0 - alpha) * y[i - 1]
    return y
