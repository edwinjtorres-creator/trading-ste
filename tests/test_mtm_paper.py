from datetime import datetime, timezone

from ste.contracts import Bar, OrderIntent, OrderSide
from ste.execution import SequentialMarkToMarket


def _bar(close: float, i: int = 0) -> Bar:
    d = datetime(2020, 1, 1 + i, tzinfo=timezone.utc)
    return Bar("X", "1d", d, close, close, close, close, 1.0, {})


def test_mtm_long_profit() -> None:
    m = SequentialMarkToMarket()
    o = OrderIntent("X", OrderSide.BUY, 1.0, _bar(100, 0).open_time_utc, "k1", "")
    m.execute(o, _bar(100.0, 0))
    r = m.execute(
        OrderIntent("X", OrderSide.BUY, 1.0, _bar(110, 1).open_time_utc, "k2", ""),
        _bar(110.0, 1),
    )
    assert r.pnl_fraccion > 0.0
    assert m.position() > 0.0
