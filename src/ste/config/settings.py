from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Settings:
    """
    Configuración global *sin* dependencia dura de Pydantic (carga en *live* añadirá
    `pydantic-settings` o variables de entorno reales en el contenedor).
    """

    ste_env: str = field(default_factory=lambda: os.environ.get("STE_ENV", "dev"))
    paper: bool = field(
        default_factory=lambda: os.environ.get("STE_PAPER", "1").lower() in ("1", "true", "yes")
    )
    kill_switch: bool = field(
        default_factory=lambda: os.environ.get("STE_KILL", "0").lower() in ("1", "true")
    )
    data_dir: str = field(default_factory=lambda: os.environ.get("STE_DATA_DIR", "data"))


_s: Settings | None = None


def get_settings() -> Settings:
    global _s
    if _s is None:
        _s = Settings()
    return _s


def reset_settings() -> None:
    global _s
    _s = None
