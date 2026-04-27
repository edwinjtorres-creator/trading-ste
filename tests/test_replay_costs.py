import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ste.contracts import Bar
from ste.eval.paper_replay import replay_parquet_mtm
from ste.ingest.parquet_store import write_bars
from ste.risk import PolicyConfig


def _make_parquet(tmp_path: Path) -> Path:
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    closes = 100.0 + 0.2 * np.random.default_rng(1).standard_normal(60)
    bars: list[Bar] = []
    for i, cl in enumerate(closes):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        hi = max(o, float(cl)) * 1.001
        lo = min(o, float(cl)) * 0.999
        bars.append(Bar("COST", "1d", d, o, hi, lo, float(cl), 1.0, {}))
    p = tmp_path / "c.parquet"
    write_bars(p, bars, run_meta={})
    return p


def test_replay_costs_reduce_equity(tmp_path: Path) -> None:
    p = _make_parquet(tmp_path)
    pol = PolicyConfig(require_regime_ok=False)
    base = replay_parquet_mtm(p, position_size=0.3, fast=5, slow=15, policy=pol)
    costly = replay_parquet_mtm(
        p,
        position_size=0.3,
        fast=5,
        slow=15,
        cost_bps=10.0,
        slippage_bps=5.0,
        policy=pol,
    )
    assert costly["total_cost_frac"] > 0.0
    assert costly["equity_final"] <= base["equity_final"]
