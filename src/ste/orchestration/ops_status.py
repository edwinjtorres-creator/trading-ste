"""
Vista operativa unificada: health + check + phase-status.
"""

from __future__ import annotations

from typing import Any

from ste import __version__
from ste.diagnostics.check import run_checks
from ste.pipeline.phases import phase_progress_report


def build_ops_status(profile: str = "api", required_modules: list[str] | None = None) -> dict[str, Any]:
    req = required_modules or []
    chk = run_checks(required_modules=req, profile=profile)
    failed_categories: list[str] = []
    if chk.core_missing:
        failed_categories.append("core")
    if chk.required_missing:
        failed_categories.append("required")
    if chk.optional_missing:
        failed_categories.append("optional")
    chk.failed_categories = failed_categories
    chk.status_code = 0 if chk.ok else 1

    phase = phase_progress_report()
    status = "ok" if chk.ok else "degraded"
    return {
        "status": status,
        "health": {"status": "ok", "version": __version__},
        "check": chk.to_jsonable(),
        "phase_progress": phase,
    }
