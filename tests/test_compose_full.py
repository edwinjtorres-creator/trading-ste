import numpy as np

from ste.contracts import OrderSide
from ste.integration import compose_full_pipeline
from ste.risk import PolicyConfig, RiskState


def test_compose_full_pipeline_intents() -> None:
    rng = np.random.default_rng(0)
    c = 100.0 + np.cumsum(0.1 * rng.standard_normal(90))
    r = RiskState()
    rows = compose_full_pipeline(
        c, r, "X", 0.25, fast=5, slow=15, policy=PolicyConfig(require_regime_ok=False)
    )
    assert len(rows) == len(c)
    last = rows[-1]
    assert "intent" in last
    assert last["side"] in (OrderSide.BUY, OrderSide.SELL, OrderSide.FLAT)
    assert last["intent"].size in (0.0, 0.25)
