from __future__ import annotations

import numpy as np
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ste.contracts import Bar
from ste.ingest.parquet_store import write_bars
from ste.jobs.walkforward_from_parquet import walkforward_report_from_parquet


def test_walkforward_from_parquet_file(tmp_path: Path) -> None:
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    closes = 100.0 + np.cumsum(0.01 * np.random.default_rng(1).standard_normal(120))
    bars: list[Bar] = []
    for i, cl in enumerate(closes):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        bars.append(
            Bar("T", "1d", d, o, o * 1.01, o * 0.99, float(cl), 1.0, {})
        )
    p = tmp_path / "x.parquet"
    write_bars(p, bars, run_meta={})
    rep = walkforward_report_from_parquet(p, train=30, test=10, step=10)
    assert len(rep) >= 1
    assert "sharpe" in rep[0] and "window" in rep[0]

    root = Path(__file__).resolve().parents[1]
    r2 = subprocess.run(
        [sys.executable, "-m", "ste", "report-wf", str(p), "--train", "30", "--test", "10", "--step", "10", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r2.returncode == 0
    assert "sharpe" in (r2.stdout or "")
