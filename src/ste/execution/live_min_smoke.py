"""
Smoke checks de LIVE_MIN sin riesgo real de capital.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ste.contracts import OrderIntent, OrderSide
from ste.execution.mt5_driver import mt5_module
from ste.execution.paper import PaperExecutor
from ste.risk import RiskState, can_trade, record_daily_pnl


def run_live_min_smoke(max_daily_loss_fraction: float = 0.01) -> dict[str, object]:
    mt5 = mt5_module()
    mt5_available = mt5 is not None

    state = RiskState(max_daily_loss_fraction=max_daily_loss_fraction)
    pre_trade_allowed = can_trade(state)
    # Simula pérdida mayor al límite para validar kill switch.
    record_daily_pnl(state, -(max_daily_loss_fraction + 0.001))
    post_trade_allowed = can_trade(state)

    paper = PaperExecutor()
    intent = OrderIntent(
        symbol="DUMMY",
        side=OrderSide.BUY,
        size=0.25,
        as_of=datetime.now(timezone.utc),
        idempotency_key="live-min-smoke",
        reason="live-min smoke test",
    )
    rep = paper.execute(intent, None)

    return {
        "mt5_available": mt5_available,
        "kill_switch": {
            "max_daily_loss_fraction": max_daily_loss_fraction,
            "pre_trade_allowed": pre_trade_allowed,
            "post_trade_allowed": post_trade_allowed,
            "trading_halt": state.trading_halt,
            "daily_pnl_fraction": state.daily_pnl_fraction,
        },
        "paper_executor": {
            "status": rep.status,
            "filled_size": rep.filled_size,
            "pnl_fraccion": rep.pnl_fraccion,
        },
        "passed": (not post_trade_allowed) and state.trading_halt,
    }
