"""
API mínima de orquestación (Fase 3+). *FastAPI* es opcional en *dev* pobre.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Lock
from time import time
from typing import Any

from ste import __version__


def build_app():
    try:
        from fastapi import Body, FastAPI, Header, HTTPException
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
    logger = logging.getLogger("ste.api")
    api_token = os.getenv("STE_API_TOKEN", "").strip()
    allowlist_raw = os.getenv("STE_REPLAY_ALLOWLIST", "").strip()
    rate_limit_per_min = int(os.getenv("STE_API_RATE_LIMIT_PER_MIN", "60"))
    audit_log_enabled = os.getenv("STE_API_AUDIT_LOG", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    rate_state: dict[str, tuple[int, int]] = {}
    rate_lock = Lock()
    allowlist_roots: list[Path] = []
    if allowlist_raw:
        for raw in allowlist_raw.split(","):
            entry = raw.strip()
            if not entry:
                continue
            p = Path(entry).expanduser()
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve(strict=False)
            else:
                p = p.resolve(strict=False)
            allowlist_roots.append(p)

    def _audit(endpoint: str, client_id: str, status: str, file_path: str = "") -> None:
        if not audit_log_enabled:
            return
        short_path = Path(file_path).name if file_path else ""
        logger.info(
            "api_access endpoint=%s client=%s status=%s file=%s",
            endpoint,
            client_id,
            status,
            short_path,
        )

    def _enforce_rate_limit(endpoint: str, client_id: str) -> None:
        if rate_limit_per_min <= 0:
            return
        now_bucket = int(time() // 60)
        key = f"{endpoint}:{client_id}"
        with rate_lock:
            bucket, count = rate_state.get(key, (now_bucket, 0))
            if bucket != now_bucket:
                bucket, count = now_bucket, 0
            count += 1
            rate_state[key] = (bucket, count)
        if count > rate_limit_per_min:
            _audit(endpoint, client_id, "rate_limited")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({rate_limit_per_min}/min)",
            )

    def _authorize_and_validate_path(
        endpoint: str,
        client_id: str,
        x_api_key: str | None,
        body: dict[str, Any],
    ) -> None:
        _enforce_rate_limit(endpoint, client_id)
        if api_token:
            got = x_api_key or ""
            if got != api_token:
                _audit(endpoint, client_id, "unauthorized")
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: missing or invalid x-api-key",
                )

        if not allowlist_roots:
            _audit(endpoint, client_id, "authorized", str(body.get("file_path", "")))
            return
        file_path = str(body.get("file_path", "")).strip()
        if not file_path:
            _audit(endpoint, client_id, "authorized")
            return
        candidate = Path(file_path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve(strict=False)
        else:
            candidate = candidate.resolve(strict=False)
        allowed = any(candidate == root or root in candidate.parents for root in allowlist_roots)
        if not allowed:
            joined = ", ".join(str(p) for p in allowlist_roots)
            _audit(endpoint, client_id, "forbidden_path", file_path)
            raise HTTPException(
                status_code=403,
                detail=f"file_path fuera de allowlist STE_REPLAY_ALLOWLIST: {joined}",
            )
        _audit(endpoint, client_id, "authorized", file_path)

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
    def replay_post(
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
        x_forwarded_for: str | None = Header(default=None, alias="x-forwarded-for"),
        data: dict[str, Any] = Body(...),
    ) -> ReplayResponse:
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

        client_id = ((x_forwarded_for or "").split(",")[0].strip()) or "local"
        _authorize_and_validate_path("/v1/replay", client_id, x_api_key, data)
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
    def eval_gate_post(
        x_api_key: str | None = Header(default=None, alias="x-api-key"),
        x_forwarded_for: str | None = Header(default=None, alias="x-forwarded-for"),
        data: dict[str, Any] = Body(...),
    ) -> EvalGateResponse:
        from ste.eval.paper_replay import evaluate_replay_gates, replay_parquet_mtm
        from ste.eval.replay_io import (
            PARQUET_REPLAY_READ_ERRORS,
            parquet_invalid_message,
            parquet_not_found_message,
        )
        from ste.risk import PolicyConfig

        client_id = ((x_forwarded_for or "").split(",")[0].strip()) or "local"
        _authorize_and_validate_path("/v1/eval-gate", client_id, x_api_key, data)
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
