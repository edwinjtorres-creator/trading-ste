"""Bares de juguete a partir de series 1D (cierre) — útil en tests e ingesta falsa v1."""

from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta, timezone

from ste.contracts import Bar

UTC = timezone.utc


def bars_from_closes_ohlc(
    closes: np.ndarray,
    symbol: str = "DUMMY",
    timeframe: str = "1h",
    t0: datetime | None = None,
    step: timedelta = timedelta(hours=1),
    extra: dict | None = None,
) -> list[Bar]:
    """
    Crea OHLC mínimo: apertura=close previo, high/max(O,C), low/min(O,C) por barra.
    """
    c = np.asarray(closes, dtype=np.float64).ravel()
    if t0 is None:
        t0 = datetime(2020, 1, 1, tzinfo=UTC)
    out: list[Bar] = []
    prev = float(c[0])
    ex = dict(extra) if extra else {}
    for i, cl in enumerate(c):
        t = t0 + i * step
        o_ = float(prev) if i > 0 else float(c[0])
        hi = float(max(o_, float(cl)))
        lo_ = float(min(o_, float(cl)))
        out.append(
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                open_time_utc=t,
                open=o_,
                high=hi,
                low=lo_,
                close=float(cl),
                volume=1.0,
                extra=ex,
            )
        )
        prev = cl
    return out
