from ste.ingest import is_valid_ohlcv


def test_ohlcv_valid() -> None:
    assert is_valid_ohlcv(1.0, 1.1, 0.9, 1.05, 1e6)
    assert not is_valid_ohlcv(1.0, 0.5, 0.9, 1.0, 1.0)
    assert not is_valid_ohlcv(1.0, 1.0, 1.0, 1.0, -1.0)
