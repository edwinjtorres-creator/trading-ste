from __future__ import annotations

import pytest

from ste.eval import WalkWindow, iter_rolling, split_indices


def test_iter_rolling_empty_when_too_short() -> None:
    # 3+2=5 > n=4, no cabe un bloque completo
    assert iter_rolling(n=4, train=3, test=2, step=1) == []
    w = iter_rolling(n=5, train=2, test=2, step=1)
    assert len(w) == 2  # (0,2)(2,4) y (1,3)(3,5)
    assert w[0] == WalkWindow(train=(0, 2), test=(2, 4))


def test_iter_rolling_windows_shape() -> None:
    w = iter_rolling(n=20, train=5, test=3, step=4)
    assert w[0] == WalkWindow(train=(0, 5), test=(5, 8))
    assert w[1] == WalkWindow(train=(4, 9), test=(9, 12))
    for win in w:
        ta, tb = win.train
        ca, cb = win.test
        assert ta < tb and ca < cb
        assert ca == ta + (tb - ta)  # test sigue a train
        rtr, rts = split_indices(win, 20)
        assert rtr is not None
        assert len(list(rtr)) + len(list(rts)) == (tb - ta) + (cb - ca)


def test_iter_rolling_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        iter_rolling(10, 0, 1, 1)
    with pytest.raises(ValueError):
        iter_rolling(10, 1, 0, 1)
