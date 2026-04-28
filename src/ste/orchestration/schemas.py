"""
Cuerpos de API (Pydantic) — importables y testeables.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ReplayRequest(BaseModel):
    """
    *Dev/local*: ruta a Parquet en el servidor. No expongas a internet sin *auth*
    y *path allowlist*.
    """

    file_path: str = Field(..., min_length=1, description="Ruta a Parquet (schema Bar)")
    position_size: float = Field(
        0.25, gt=0, le=1.0, description="Fracción de *exposure* por bar (0, 1]"
    )
    fast: int = Field(5, ge=1, description="Ventana EMA rápida (momentum)")
    slow: int = Field(15, ge=2, description="Ventana EMA lenta (debe ser > fast)")
    max_daily_loss_fraction: float = Field(
        0.01, gt=0.0, le=1.0, description="Límite de pérdida diaria fraccional para kill switch"
    )
    cost_bps: float = Field(0.0, ge=0.0, description="Coste fijo por turnover en bps")
    slippage_bps: float = Field(0.0, ge=0.0, description="Slippage por turnover en bps")
    min_sharpe: float | None = Field(None, description="Gate opcional: sharpe mínimo")
    max_drawdown: float | None = Field(
        None, ge=0.0, le=1.0, description="Gate opcional: drawdown máximo permitido"
    )
    min_equity: float | None = Field(None, gt=0.0, description="Gate opcional: equity final mínima")
    ignore_regime: bool = False

    @model_validator(mode="after")
    def slow_must_exceed_fast(self) -> ReplayRequest:
        if self.slow <= self.fast:
            raise ValueError("slow debe ser mayor que fast (misma regla que la señal)")
        return self


class HttpErrorPlain(BaseModel):
    """Cuerpo típico de `HTTPException(detail=str)` en rutas STE."""

    detail: str


class ReplayResponse(BaseModel):
    """Salida JSON de `replay_parquet_mtm` (sin numpy). Expuesta en `POST /v1/replay`."""

    n_bars: int
    equity_final: float
    equity_curve: list[float]
    returns: list[float] = Field(
        ..., description="Retornos fraccionales bar a bar (MTM *paper*)"
    )
    bar_times: list[str]
    sharpe: float
    max_drawdown: float
    total_cost_frac: float
    gate_passed: bool = True
    gate_failures: list[str] = Field(default_factory=list)
    halted: bool
    path: str


class EvalGateMetrics(BaseModel):
    equity_final: float
    sharpe: float
    max_drawdown: float
    total_cost_frac: float
    halted: bool


class EvalGateResponse(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    metrics: EvalGateMetrics
    path: str
