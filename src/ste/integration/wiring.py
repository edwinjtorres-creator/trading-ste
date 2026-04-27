from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
from datetime import datetime, timezone

from ste.contracts import Bar, OrderIntent, OrderSide, RegimeAction, RegimeView
from ste.execution.paper import PaperExecutor
from ste.risk import PolicyConfig, RiskState, can_trade, decide, record_daily_pnl
from ste.regime.hurst import regime_gating_from_hurst, rough_hurst
from ste.signal.momentum import momentum_signal


def build_idempotency_key(bar: Bar, tag: str) -> str:
    return f"{bar.symbol}|{bar.open_time_utc.isoformat()}|{tag}"


def compose_signal_risk(
    closes: np.ndarray,
    risk: RiskState,
) -> list[tuple[Bar, dict]]:
    """
    Tubería mínima de *research*: velas *sintéticas* → Hurst + momentum; sin órdenes.
    """
    from ste.ingest.synthetic import bars_from_closes_ohlc

    bars = bars_from_closes_ohlc(
        closes, symbol="WIRE", t0=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    m = momentum_signal(closes, fast=5, slow=15) if closes.size else np.array([], dtype=int)
    out: list[tuple[Bar, dict]] = []
    for i, b in enumerate(bars):
        w = closes[max(0, i - 128) : i + 1]
        h = rough_hurst(w) if w.size >= 32 else float("nan")
        g = regime_gating_from_hurst(h)
        rview = RegimeView(
            b.open_time_utc,
            RegimeAction.OK if g == "ok" else RegimeAction.AVOID,
            "hurst1",
        )
        mom = int(m[i] if m.size == len(bars) and i < m.size else 0)
        feat = {
            "hurst": h,
            "regime": g,
            "momentum": mom,
            "rview": rview,
        }
        out.append((b, feat))
    return out


def iter_pipeline_rows(
    closes: np.ndarray,
    risk: RiskState,
    symbol: str,
    position_size: float,
    t0: datetime,
    fast: int = 5,
    slow: int = 15,
    policy: PolicyConfig | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Misma lógica que *compose* pero *lazy*; `risk` se lee en `decide` (útil con
    *halt* en *replay* secuencial).
    """
    from ste.ingest.synthetic import bars_from_closes_ohlc

    bars = bars_from_closes_ohlc(closes, symbol=symbol, t0=t0)
    m = momentum_signal(closes, fast=fast, slow=slow) if closes.size else np.array([], dtype=int)
    cfg = policy or PolicyConfig()
    for i, b in enumerate(bars):
        w = closes[max(0, i - 128) : i + 1]
        h = rough_hurst(w) if w.size >= 32 else float("nan")
        g = regime_gating_from_hurst(h)
        rview = RegimeView(
            b.open_time_utc,
            RegimeAction.OK if g == "ok" else RegimeAction.AVOID,
            "hurst1",
        )
        mom = int(m[i] if m.size == len(bars) and i < m.size else 0)
        side, reason = decide(risk, rview, mom, cfg)
        size = 0.0 if side is OrderSide.FLAT else float(position_size)
        intent = OrderIntent(
            symbol=symbol,
            side=side,
            size=size,
            as_of=b.open_time_utc,
            idempotency_key=build_idempotency_key(b, "pipe"),
            reason=reason,
        )
        yield {
            "bar": b,
            "hurst": h,
            "regime": g,
            "momentum": mom,
            "rview": rview,
            "side": side,
            "policy_reason": reason,
            "intent": intent,
        }


def compose_full_pipeline(
    closes: np.ndarray,
    risk: RiskState,
    symbol: str,
    position_size: float,
    t0: datetime | None = None,
    fast: int = 5,
    slow: int = 15,
    policy: PolicyConfig | None = None,
) -> list[dict[str, Any]]:
    """
    Señal + régimen + `decide` → `OrderIntent` por vela (transversal: un mismo
    `RiskState` *sin* P&L acumulado salvo lo que tenga ya `halt`).
    """
    if t0 is None:
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return list(
        iter_pipeline_rows(
            closes, risk, symbol, position_size, t0, fast, slow, policy
        )
    )


def paper_round_if_allowed(
    intent: OrderIntent, risk: RiskState, last_bar: Bar, executor: PaperExecutor
) -> dict:
    if not can_trade(risk):
        return {"ok": False, "reason": "kill_or_risk", "report": None}
    rep = executor.execute(intent, last_bar)
    record_daily_pnl(risk, rep.pnl_fraccion)
    return {"ok": True, "report": rep}
