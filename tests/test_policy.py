from datetime import datetime, timezone

from ste.contracts import RegimeAction, RegimeView, OrderSide
from ste.risk import PolicyConfig, RiskState, decide, record_daily_pnl


def _rv(ok: bool) -> RegimeView:
    a = RegimeAction.OK if ok else RegimeAction.AVOID
    return RegimeView(datetime(2020, 1, 1, tzinfo=timezone.utc), a, "t")


def test_decide_halt() -> None:
    r = RiskState()
    record_daily_pnl(r, -1.0)
    side, reason = decide(r, _rv(True), 1, PolicyConfig())
    assert side is OrderSide.FLAT
    assert reason == "risk_halt"


def test_decide_regime() -> None:
    r = RiskState()
    side, reason = decide(r, _rv(False), 1, PolicyConfig(require_regime_ok=True))
    assert side is OrderSide.FLAT
    assert reason == "regime_avoid"


def test_decide_momentum() -> None:
    r = RiskState()
    side, _ = decide(r, _rv(True), 1, PolicyConfig())
    assert side is OrderSide.BUY
    side, _ = decide(r, _rv(True), -1, PolicyConfig())
    assert side is OrderSide.SELL
