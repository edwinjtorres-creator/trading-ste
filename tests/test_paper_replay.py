from __future__ import annotations

import json
import numpy as np
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ste.contracts import Bar
from ste.eval.paper_replay import replay_parquet_mtm
from ste.ingest.parquet_store import write_bars
from ste.risk import PolicyConfig


def test_replay_parquet_mtm_runs(tmp_path: Path) -> None:
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    c = 100.0 + np.cumsum(0.1 * np.random.default_rng(2).standard_normal(50))
    bars: list[Bar] = []
    for i, cl in enumerate(c):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        hi = max(o, float(cl)) * 1.001
        lo = min(o, float(cl)) * 0.999
        bars.append(Bar("T", "1d", d, o, hi, lo, float(cl), 1.0, {}))
    p = tmp_path / "r.parquet"
    write_bars(p, bars, run_meta={})
    o = replay_parquet_mtm(p, position_size=0.2, policy=PolicyConfig(require_regime_ok=False))
    assert o["n_bars"] == 50
    assert o["equity_final"] > 0
    assert len(o["equity_curve"]) == o["n_bars"] or len(o["equity_curve"]) == 1 + len(o["returns"])
    # curve starts at 1.0, one per step, so 1 + n *iterations - for each bar one iteration, curve len 51? 
    # we append after each of n iterations -> curve starts [1.0] then n appends = n+1
    assert len(o["returns"]) + 1 == len(o["equity_curve"])
    root = Path(__file__).resolve().parents[1]
    r2 = subprocess.run(
        [sys.executable, "-m", "ste", "replay", str(p), "--json", "--ignore-regime"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r2.returncode == 0
    d = json.loads(r2.stdout)
    assert "equity_final" in d


