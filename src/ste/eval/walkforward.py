"""
Walk-forward: ventana de entrenamiento fija + prueba, deslizando por el tiempo.

*Índices* sobre 0..n-1: útiles para *arrays* y bares alineados por fila.
Sin mirar hacia adelante dentro del bloque *train* al ajustar el modelo (eso es
tarea de la capa de *backtest* que consuma esta API).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WalkWindow:
    """Rangos *half-open* [a, b) en índice de filas."""

    train: tuple[int, int]  # [start, end) train
    test: tuple[int, int]  # [start, end) test (justo a continuación o solapar según modo)


def iter_rolling(
    n: int,
    train: int,
    test: int,
    step: int,
) -> list[WalkWindow]:
    """
    Ventana deslizante: para cada inicio *start* (en pasos *step*):

    - *train* filas: [start, start+train)
    - *test* filas:  [start+train, start+train+test)

    Requisitos: n >= train + test, train >= 1, test >= 1, step >= 1.
    """
    if n < 0 or train < 1 or test < 1 or step < 1:
        raise ValueError("parámetros inválidos de walk-forward")
    if n < train + test:
        return []
    out: list[WalkWindow] = []
    s = 0
    while s + train + test <= n:
        a, b, c, d = s, s + train, s + train, s + train + test
        out.append(
            WalkWindow(
                train=(a, b),
                test=(c, d),
            )
        )
        s += step
    return out


def walk_window_to_dict(w: WalkWindow) -> dict[str, list[int]]:
    """Serialización estable (p. ej. *JSON* en *CLI* o logs)."""
    return {
        "train": [w.train[0], w.train[1]],
        "test": [w.test[0], w.test[1]],
    }


def split_indices(
    w: WalkWindow, n: int
) -> tuple[range, range] | None:
    """Convierte a `range` reutilizables; devuelve None si fuera de [0, n)."""
    ta, tb = w.train
    ca, cb = w.test
    if ta < 0 or cb > n or ta >= tb or ca >= cb:
        return None
    return range(ta, tb), range(ca, cb)
