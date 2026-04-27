import numpy as np

from ste.eval.metrics import max_drawdown, sharpe_ratio


def test_sharpe_not_nan_on_constant_zero() -> None:
    r = np.zeros(10)
    assert np.isfinite(sharpe_ratio(r))


def test_max_drawdown_in_zero_one() -> None:
    r = np.array([0.1, -0.2, 0.05, 0.0, -0.1])
    d = max_drawdown(r)
    assert 0.0 <= d <= 1.0
