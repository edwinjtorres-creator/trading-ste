from datetime import datetime, timezone

from ste.contracts import Bar, OrderIntent, OrderSide, utcnow
from ste.execution.paper import PaperExecutor
from ste.risk import RiskState, can_trade, record_daily_pnl, reset_state


def _bar() -> Bar:
    d = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Bar("X", "1h", d, 1.0, 1.1, 0.9, 1.0, 1.0, {})


def test_paper_fills() -> None:
    ex = PaperExecutor()
    r = ex.execute(
        OrderIntent("X", OrderSide.BUY, 0.5, utcnow(), "k1"),
        _bar(),
    )
    assert r.status in ("filled", "rejected")
    assert r.intent_idempotency_key == "k1"


def test_paper_risk_stops() -> None:
    risk = RiskState(max_daily_loss_fraction=0.01)
    record_daily_pnl(risk, -0.02)
    assert not can_trade(risk)
    reset_state(risk)
    assert can_trade(risk)
