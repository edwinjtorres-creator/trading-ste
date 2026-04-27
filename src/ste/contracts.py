"""
Tipos mínimos compartidos entre capas (ingesta, señal, riesgo, eval, ejecución).

Cualquier boundary nuevo debe o bien usar estos modelos, o ampliar este módulo con
cuidado (versionar cambios estructurales en experimentos, no al vuelo en *live*).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Symbol(StrEnum):
    """Identificador de instumento: extender o usar string libre vía *extra*."""

    DUMMY = "DUMMY"


@dataclass(frozen=True, slots=True)
class Bar:
    """
    Vela *canonical*; tiempos en **UTC** (cierre o apertura según convención del
    *ingestor*, pero siempre coherente en toda la tubería).
    """

    symbol: str
    timeframe: str  # ej. "1h", "1m", "1d"
    open_time_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SignalBatch:
    """
    Intención de *alpha*; **no** implica que la política permita operar hoy.
    Generado por *signal/regime*; *risk/policy* decidirá órdenes o *flat*.
    """

    as_of: datetime
    values: dict[str, float]  # ej. {"momentum": 1.0, "hurst": 0.55}
    meta: Mapping[str, Any] = field(default_factory=dict)


class RegimeAction(StrEnum):
    OK = "ok"
    AVOID = "avoid"


@dataclass(frozen=True, slots=True)
class RegimeView:
    """Vista de régimen listo para unir con riesgo (Hurst, HMM, mezcla)."""

    as_of: datetime
    action: RegimeAction
    name: str = "default"
    details: Mapping[str, Any] = field(default_factory=dict)


class OrderSide(StrEnum):
    FLAT = "flat"
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """
    *Intent* post-policy; el *execution adapter* (sim o real) vuelve *OrderReport*.

    Tamaño en fracción o unidades, según acuerde el *broker* y la capa de riesgo.
    """

    symbol: str
    side: OrderSide
    size: float
    as_of: datetime
    idempotency_key: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class OrderReport:
    """Cierre o parte del ciclo: lo que ocurrió (simulado o real) para el *ledger*."""

    intent_idempotency_key: str
    status: str  # e.g. "filled", "rejected", "partial"
    filled_size: float
    price: float | None
    pnl_fraccion: float
    as_of: datetime
    details: Mapping[str, Any] = field(default_factory=dict)
