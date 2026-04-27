import numpy as np

from ste.signal.momentum import momentum_signal


def test_momentum_shape_and_values() -> None:
    rng = np.random.default_rng(0)
    closes = np.cumsum(rng.standard_normal(80)) + 100.0
    out = momentum_signal(closes, fast=5, slow=15)
    assert out.shape == closes.shape
    assert set(np.unique(out)) <= {-1, 0, 1} or set(np.unique(out)) <= {-1, 1}
