from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from ste.contracts import Bar
from ste.ingest import (
    read_bars,
    read_bars_metadata,
    write_bars,
)
from ste.ingest.synthetic import bars_from_closes_ohlc


def _bar() -> Bar:
    return Bar(
        symbol="EURUSD",
        timeframe="1h",
        open_time_utc=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.05,
        volume=1_000.0,
        extra={"src": "test", "n": 1},
    )


def test_bars_parquet_roundtrip_idempotent(tmp_path: Path) -> None:
    a = _bar()
    p = tmp_path / "a.parquet"
    write_bars(
        p,
        [a],
        run_meta={"source": "pytest", "note": "roundtrip"},
    )
    back = read_bars(p)
    assert len(back) == 1
    b = back[0]
    assert b.symbol == a.symbol
    assert b.timeframe == a.timeframe
    assert b.open == a.open and b.high == a.high and b.low == a.low and b.close == a.close
    assert b.volume == a.volume
    assert b.extra == a.extra
    # Tiempo: mismo instante
    assert b.open_time_utc == a.open_time_utc
    m = read_bars_metadata(p)
    assert m is not None
    assert m.n_rows == 1
    assert m.custom.get("source") == "pytest"


def test_synthetic_then_roundtrip_multi(tmp_path: Path) -> None:
    c = 100.0 + np.cumsum(np.array([0.0, 0.1, -0.2, 0.05, 0.0]))
    bars = bars_from_closes_ohlc(
        c,
        symbol="X",
        t0=datetime(2019, 1, 1, 0, tzinfo=timezone.utc),
    )
    p = tmp_path / "b.parquet"
    write_bars(p, bars, run_meta={})
    again = read_bars(p)
    assert len(again) == len(bars)
    for x, y in zip(bars, again, strict=True):
        assert x.symbol == y.symbol
        assert x.open_time_utc == y.open_time_utc
        assert abs(x.close - y.close) < 1e-12
