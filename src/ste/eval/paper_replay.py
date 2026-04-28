from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from ste.eval.metrics import max_drawdown, sharpe_ratio
from ste.execution.mtm_paper import SequentialMarkToMarket
from ste.ingest.parquet_store import read_bars
from ste.integration.wiring import iter_pipeline_rows
from ste.risk import PolicyConfig, RiskState, can_trade, record_daily_pnl


def replay_parquet_mtm(
    path: str | Path,
    position_size: float = 0.25,
    fast: int = 5,
    slow: int = 15,
    max_daily_loss_fraction: float = 0.01,
    cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
    policy: PolicyConfig | None = None,
) -> dict[str, Any]:
    """
    *Replay* bar a bar: política + `SequentialMarkToMarket` + riesgo diario
    (mismo `record_daily_pnl` que *live* paper). Devuelve curva de *equity*,
    métricas y bandera *halted*.
    """
    p = Path(path)
    bars = sorted(read_bars(p), key=lambda b: b.open_time_utc)
    if len(bars) < 2:
        return {
            "n_bars": len(bars),
            "equity_final": 1.0,
            "equity_curve": [1.0],
            "returns": np.array([], dtype=np.float64),
            "bar_times": [],
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "total_cost_frac": 0.0,
            "halted": False,
            "path": str(p),
        }
    sym = bars[0].symbol
    t0 = bars[0].open_time_utc
    closes = np.array([b.close for b in bars], dtype=np.float64)
    risk = RiskState(max_daily_loss_fraction=float(max_daily_loss_fraction))
    mtm = SequentialMarkToMarket()
    cfg = policy or PolicyConfig()
    curve: list[float] = [1.0]
    rets: list[float] = []
    times: list[str] = []
    halted = False
    total_cost_frac = 0.0
    bps_frac = (float(cost_bps) + float(slippage_bps)) / 10_000.0
    for row in iter_pipeline_rows(
        closes, risk, sym, position_size, t0, fast, slow, cfg
    ):
        if not can_trade(risk):
            halted = True
            break
        pos_before = mtm.position()
        rep = mtm.execute(row["intent"], row["bar"])
        pos_after = mtm.position()
        turnover = abs(pos_after - pos_before)
        cost_frac = turnover * bps_frac
        pnl_net = float(rep.pnl_fraccion) - float(cost_frac)
        total_cost_frac += float(cost_frac)
        record_daily_pnl(risk, pnl_net)
        last = curve[-1]
        next_e = last * (1.0 + pnl_net)
        curve.append(float(next_e))
        rets.append(float(pnl_net))
        times.append(row["bar"].open_time_utc.isoformat())
    arr = np.asarray(rets, dtype=np.float64)
    eq = float(curve[-1]) if curve else 1.0
    return {
        "n_bars": len(bars),
        "equity_final": eq,
        "equity_curve": curve,
        "returns": arr,
        "bar_times": times,
        "sharpe": float(sharpe_ratio(arr)) if arr.size > 1 else 0.0,
        "max_drawdown": float(max_drawdown(arr)) if arr.size > 1 else 0.0,
        "total_cost_frac": float(total_cost_frac),
        "halted": halted,
        "path": str(p),
    }


def write_replay_csv(result: dict[str, Any], csv_path: str | Path) -> None:
    """Escribe *open_time_utc, pnl_fraccion, equity_after* (una fila por paso *replay*)."""
    p = Path(csv_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    times: list[str] = list(result.get("bar_times") or [])
    rets = result["returns"]
    curve: list[float] = list(result["equity_curve"])
    if hasattr(rets, "tolist"):
        rets = rets.tolist()  # type: ignore[assignment]
    n = min(len(times), len(rets), max(0, len(curve) - 1))
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["open_time_utc", "pnl_fraccion", "equity_after"])
        for i in range(n):
            w.writerow([times[i], rets[i], curve[i + 1]])


def replay_to_jsonable(result: dict[str, Any]) -> dict[str, Any]:
    """Convierte *numpy* y tipos raros a JSON-seguro."""
    out: dict[str, Any] = {}
    for k, v in result.items():
        if k == "returns" and hasattr(v, "tolist"):
            out[k] = v.tolist()  # type: ignore[union-attr]
        else:
            out[k] = v
    return out


def evaluate_replay_gates(
    result: dict[str, Any],
    *,
    min_sharpe: float | None = None,
    max_drawdown: float | None = None,
    min_equity: float | None = None,
) -> list[str]:
    failures: list[str] = []
    if min_sharpe is not None and float(result.get("sharpe", 0.0)) < float(min_sharpe):
        failures.append(
            f"sharpe {float(result.get('sharpe', 0.0)):.4f} < min_sharpe {float(min_sharpe):.4f}"
        )
    if max_drawdown is not None and float(result.get("max_drawdown", 0.0)) > float(max_drawdown):
        failures.append(
            "max_drawdown "
            f"{float(result.get('max_drawdown', 0.0)):.4f} > max_drawdown {float(max_drawdown):.4f}"
        )
    if min_equity is not None and float(result.get("equity_final", 1.0)) < float(min_equity):
        failures.append(
            f"equity_final {float(result.get('equity_final', 1.0)):.6f} < min_equity {float(min_equity):.6f}"
        )
    return failures
