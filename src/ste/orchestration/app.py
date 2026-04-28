"""
API mínima de orquestación (Fase 3+). *FastAPI* es opcional en *dev* pobre.
"""

from __future__ import annotations

from typing import Any

from ste import __version__


def build_app():
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.encoders import jsonable_encoder
    except ImportError as e:
        raise RuntimeError("Instala *fastapi* (requirements/layers/04) para la API") from e
    from pydantic import ValidationError

    from ste.orchestration.schemas import (
        EvalGateResponse,
        HttpErrorPlain,
        ReplayRequest,
        ReplayResponse,
    )

    app = FastAPI(title="STE", version=__version__)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/phase")
    def phase() -> dict[str, int | str]:
        from ste.pipeline.phases import Phase, phase_descriptions
        p: Phase = Phase.NUCLEO
        return {"phase": int(p), "description": phase_descriptions()[p]}

    @app.get("/ops/status")
    def ops_status(profile: str = "api", require: str = "") -> dict[str, Any]:
        from ste.orchestration.ops_status import build_ops_status

        req = [m.strip() for m in require.split(",") if m.strip()]
        return build_ops_status(profile=profile, required_modules=req)

    @app.post(
        "/v1/replay",
        response_model=ReplayResponse,
        responses={
            400: {
                "model": HttpErrorPlain,
                "description": "Parquet ilegible o no compatible con el schema STE",
            },
            404: {"model": HttpErrorPlain, "description": "Ruta inexistente"},
            422: {"description": "JSON inválido o parámetros fuera de rango"},
        },
    )
    def replay_post(data: dict[str, Any] = Body(...)) -> ReplayResponse:
        from ste.eval.paper_replay import (
            evaluate_replay_gates,
            replay_parquet_mtm,
            replay_to_jsonable,
        )
        from ste.eval.replay_io import (
            PARQUET_REPLAY_READ_ERRORS,
            parquet_invalid_message,
            parquet_not_found_message,
        )
        from ste.risk import PolicyConfig

        try:
            payload = ReplayRequest.model_validate(data)
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail=jsonable_encoder(e.errors())
            ) from e
        pol = PolicyConfig(require_regime_ok=not payload.ignore_regime)
        try:
            res = replay_parquet_mtm(
                payload.file_path,
                position_size=payload.position_size,
                fast=payload.fast,
                slow=payload.slow,
                max_daily_loss_fraction=payload.max_daily_loss_fraction,
                cost_bps=payload.cost_bps,
                slippage_bps=payload.slippage_bps,
                policy=pol,
            )
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=parquet_not_found_message(e, payload.file_path),
            ) from e
        except PARQUET_REPLAY_READ_ERRORS as e:
            raise HTTPException(
                status_code=400,
                detail=parquet_invalid_message(e),
            ) from e
        gate_failures = evaluate_replay_gates(
            res,
            min_sharpe=payload.min_sharpe,
            max_drawdown=payload.max_drawdown,
            min_equity=payload.min_equity,
        )
        res["gate_passed"] = len(gate_failures) == 0
        res["gate_failures"] = gate_failures
        return ReplayResponse.model_validate(replay_to_jsonable(res))

    @app.post(
        "/v1/eval-gate",
        response_model=EvalGateResponse,
        responses={
            400: {
                "model": HttpErrorPlain,
                "description": "Parquet ilegible o no compatible con el schema STE",
            },
            404: {"model": HttpErrorPlain, "description": "Ruta inexistente"},
            422: {"description": "JSON inválido o parámetros fuera de rango"},
        },
    )
    def eval_gate_post(data: dict[str, Any] = Body(...)) -> EvalGateResponse:
        from ste.eval.paper_replay import evaluate_replay_gates, replay_parquet_mtm
        from ste.eval.replay_io import (
            PARQUET_REPLAY_READ_ERRORS,
            parquet_invalid_message,
            parquet_not_found_message,
        )
        from ste.risk import PolicyConfig

        try:
            payload = ReplayRequest.model_validate(data)
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail=jsonable_encoder(e.errors())
            ) from e
        pol = PolicyConfig(require_regime_ok=not payload.ignore_regime)
        try:
            res = replay_parquet_mtm(
                payload.file_path,
                position_size=payload.position_size,
                fast=payload.fast,
                slow=payload.slow,
                max_daily_loss_fraction=payload.max_daily_loss_fraction,
                cost_bps=payload.cost_bps,
                slippage_bps=payload.slippage_bps,
                policy=pol,
            )
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=parquet_not_found_message(e, payload.file_path),
            ) from e
        except PARQUET_REPLAY_READ_ERRORS as e:
            raise HTTPException(
                status_code=400,
                detail=parquet_invalid_message(e),
            ) from e
        failures = evaluate_replay_gates(
            res,
            min_sharpe=payload.min_sharpe,
            max_drawdown=payload.max_drawdown,
            min_equity=payload.min_equity,
        )
        payload_out = {
            "passed": len(failures) == 0,
            "failures": failures,
            "metrics": {
                "equity_final": float(res.get("equity_final", 1.0)),
                "sharpe": float(res.get("sharpe", 0.0)),
                "max_drawdown": float(res.get("max_drawdown", 0.0)),
                "total_cost_frac": float(res.get("total_cost_frac", 0.0)),
                "halted": bool(res.get("halted", False)),
            },
            "path": str(res.get("path", payload.file_path)),
        }
        return EvalGateResponse.model_validate(payload_out)

    return app
