"""
Descarga OHLC vía *yfinance*. Requiere `yfinance` + *pandas*.
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from ste.contracts import Bar
from ste.ingest.parquet_store import write_bars

# Subconjuntos documentados comunes (yfinance admite más; validación blanda)
_VALID_PERIODS = frozenset(
    {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
)
_VALID_INTERVALS = frozenset(
    {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }
)


def _row_to_utc_open(row_name, tz_exch: str) -> datetime:
    import pandas as pd

    ts = pd.Timestamp(row_name)
    if ts.tzinfo is None:
        ts = ts.tz_localize(ZoneInfo(tz_exch))
    return ts.tz_convert(timezone.utc).to_pydatetime()


def is_valid_ohlcv(o: float, h: float, l_: float, c: float, v: float) -> bool:
    if not all(np.isfinite(x) for x in (o, h, l_, c, v)):
        return False
    if o <= 0 or h <= 0 or l_ <= 0 or c <= 0:
        return False
    if h < l_:
        return False
    if h < max(o, c) or l_ > min(o, c):
        return False
    if v < 0:
        return False
    return True


def download_ohlc_to_parquet(
    ticker: str,
    path: str | Path,
    period: str = "1y",
    interval: str = "1d",
    symbol: str | None = None,
    timeframe: str = "1d",
    exchange_tz: str = "America/New_York",
    run_meta: dict | None = None,
    validate_rows: bool = True,
) -> int:
    """
    Descarga historial, valida filas (OHLC coherente, volumen ≥ 0) y escribe *Parquet*.

    Líneas inválidas se omiten (y se avisa con *warnings*).
    """
    if period not in _VALID_PERIODS:
        warnings.warn(f"period={period!r} no está en el conjunto revisado STE; comprobar yfinance.", stacklevel=2)
    if interval not in _VALID_INTERVALS:
        warnings.warn(f"interval={interval!r} no está en el conjunto revisado STE; comprobar yfinance.", stacklevel=2)

    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError("Instalá yfinance: pip install yfinance (o capa 04-connect-exec).") from e

    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df is None or len(df) < 1:
        raise ValueError(f"sin datos para {ticker!r} (period={period!r} interval={interval!r})")

    sym = symbol or ticker.replace("/", "-")
    bars: list[Bar] = []
    dropped = 0
    for idx, row in df.iterrows():
        o = float(row["Open"])
        h = float(row["High"])
        l_ = float(row["Low"])
        c = float(row["Close"])
        try:
            v = float(row["Volume"])
        except (KeyError, TypeError, ValueError):
            v = 0.0
        if validate_rows and not is_valid_ohlcv(o, h, l_, c, v):
            dropped += 1
            continue
        dt = _row_to_utc_open(idx, exchange_tz)
        bars.append(
            Bar(
                symbol=sym,
                timeframe=timeframe,
                open_time_utc=dt,
                open=o,
                high=h,
                low=l_,
                close=c,
                volume=v,
                extra={"source": "yfinance", "ticker": ticker},
            )
        )
    if dropped:
        warnings.warn(f"{ticker}: descartadas {dropped} filas por OHLC/volumen inválido.", stacklevel=2)
    if not bars:
        raise ValueError(f"sin bares válidos tras validación para {ticker!r}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {**(run_meta or {}), "ticker": ticker, "period": period, "interval": interval, "dropped_rows": dropped}
    write_bars(path, bars, run_meta=meta)
    return len(bars)


def download_many_to_parquet(
    tickers: list[str],
    out_dir: str | Path,
    period: str = "1y",
    interval: str = "1d",
    exchange_tz: str = "America/New_York",
    validate_rows: bool = True,
) -> list[tuple[str, Path, int]]:
    """
    Un archivo por ticker: ``{out_dir}/{SYMBOL}.parquet``. Devuelve lista
    ``(ticker, path, n_bares)``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out: list[tuple[str, Path, int]] = []
    for raw in tickers:
        t = raw.strip().upper()
        safe = t.replace("/", "-")
        p = out_dir / f"{safe}.parquet"
        n = download_ohlc_to_parquet(
            t,
            p,
            period=period,
            interval=interval,
            exchange_tz=exchange_tz,
            validate_rows=validate_rows,
        )
        out.append((t, p, n))
    return out
