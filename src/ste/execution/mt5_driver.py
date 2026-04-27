"""
Puente hacia *MetaTrader5* (sólo en Windows, librería opcional). Import *lazy*
para no romper *CI* o Linux.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

_m: ModuleType | None = None


def mt5_module() -> Any | None:
    global _m
    if _m is not None:
        return _m
    try:
        import MetaTrader5  # type: ignore[import-not-found, import-untyped]
    except Exception:
        return None
    _m = MetaTrader5
    return _m
