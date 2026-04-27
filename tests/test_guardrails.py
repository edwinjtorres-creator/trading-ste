from ste.risk import RiskState, can_trade, record_daily_pnl, reset_state


def test_trading_stops_after_daily_loss_limit() -> None:
    s = RiskState(max_daily_loss_fraction=0.02)
    assert can_trade(s)
    record_daily_pnl(s, -0.015)
    assert can_trade(s)
    record_daily_pnl(s, -0.01)
    assert s.daily_pnl_fraction == -0.025
    assert s.trading_halt
    assert not can_trade(s)


def test_reset_clears_halt() -> None:
    s = RiskState(max_daily_loss_fraction=0.01)
    record_daily_pnl(s, -0.02)
    assert not can_trade(s)
    reset_state(s)
    assert can_trade(s)
    assert s.daily_pnl_fraction == 0.0
    assert s.equity == 1.0
