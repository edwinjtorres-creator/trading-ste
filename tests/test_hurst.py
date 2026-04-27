import numpy as np

from ste.regime.hurst import regime_gating_from_hurst, rough_hurst


def test_rough_hurst_is_finite_for_long_series() -> None:
    rng = np.random.default_rng(1)
    n = 500
    # camino log-Browniano (aprox) — precios log-positivos
    logp = np.cumsum(0.01 * rng.standard_normal(n))
    h = rough_hurst(logp)
    assert h == h
    assert 0.01 < h <= 0.99


def test_rough_hurst_short_series_is_nan() -> None:
    assert np.isnan(rough_hurst(np.array([1.0, 2.0, 3.0])))


def test_regime_gating() -> None:
    assert regime_gating_from_hurst(0.5) == "ok"  # dentro de 0.40–0.60
    assert regime_gating_from_hurst(0.1) == "avoid"
    assert regime_gating_from_hurst(float("nan")) == "avoid"
