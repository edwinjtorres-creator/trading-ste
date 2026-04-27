"""
Fases 0–4: referencia a `docs/ARCHITECTURE.md`. Código solo enumera; no sustituye
*gate* de negocio.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any


class Phase(IntEnum):
    NUCLEO = 0
    INGESTA_ESQUEMA = 1
    EVALUACION = 2
    ORQUESTACION_PAPER = 3
    LIVE_MIN = 4


def phase_descriptions() -> dict[int, str]:
    return {
        Phase.NUCLEO: "Núcleo, tests, riesgo y contratos; sin conexión broker",
        Phase.INGESTA_ESQUEMA: "Ingesta reproducible y esquemas; Parquet, línea base de datos",
        Phase.EVALUACION: "Backtest, walk-forward, sombra y métricas; sin riesgo real de mercado aún con live sim",
        Phase.ORQUESTACION_PAPER: "API, tareas, paper 24/7; health y kill *probados*",
        Phase.LIVE_MIN: "Ejecución mínima con riesgo acotado y *adapter* a broker; sin autopiloto ciego de código",
    }


def validate_phase(p: int) -> bool:
    return 0 <= int(p) <= 4


@dataclass(frozen=True)
class PhaseStatus:
    phase: int
    name: str
    description: str
    ready: bool
    evidence: list[str]
    missing: list[str]
    next_actions: list[str]
    completed_actions: list[str]
    action_progress: dict[str, int]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "name": self.name,
            "description": self.description,
            "ready": self.ready,
            "evidence": self.evidence,
            "missing": self.missing,
            "next_actions": self.next_actions,
            "completed_actions": self.completed_actions,
            "action_progress": self.action_progress,
        }


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _checklist_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "PHASES_CHECKLIST.json"


def _load_phase_checklist() -> dict[int, dict[str, Any]]:
    p = _checklist_path()
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for k, v in raw.items():
        try:
            ki = int(k)
        except Exception:
            continue
        if not isinstance(v, dict):
            continue
        out[ki] = v
    return out


def _normalize_actions_for_write(raw_actions: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in raw_actions:
        if isinstance(it, str):
            s = it.strip()
            if s:
                out.append({"text": s, "done": False})
            continue
        if not isinstance(it, dict):
            continue
        text = str(it.get("text", "")).strip()
        if not text:
            continue
        out.append({"text": text, "done": bool(it.get("done", False))})
    return out


def set_phase_action_done(phase: int, action_text: str, done: bool) -> bool:
    """Marca acción como done/pending dentro de `docs/PHASES_CHECKLIST.json`."""
    p = _checklist_path()
    raw: dict[str, Any]
    if p.exists():
        try:
            raw_obj = json.loads(p.read_text(encoding="utf-8"))
            raw = raw_obj if isinstance(raw_obj, dict) else {}
        except Exception:
            raw = {}
    else:
        raw = {}
    key = str(int(phase))
    entry = raw.get(key)
    if not isinstance(entry, dict):
        return False
    acts = entry.get("next_actions")
    if not isinstance(acts, list):
        return False
    norm = _normalize_actions_for_write(acts)
    target = action_text.strip()
    changed = False
    for item in norm:
        if item["text"] == target:
            item["done"] = bool(done)
            changed = True
            break
    if not changed:
        return False
    entry["next_actions"] = norm
    raw[key] = entry
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _split_actions(raw_actions: list[Any]) -> tuple[list[str], list[str]]:
    pending: list[str] = []
    completed: list[str] = []
    for it in raw_actions:
        if isinstance(it, str):
            pending.append(it)
            continue
        if not isinstance(it, dict):
            continue
        text = str(it.get("text", "")).strip()
        if not text:
            continue
        if bool(it.get("done", False)):
            completed.append(text)
        else:
            pending.append(text)
    return pending, completed


def assess_phase_statuses() -> list[PhaseStatus]:
    desc = phase_descriptions()
    statuses: list[PhaseStatus] = []
    checks: dict[Phase, tuple[list[str], list[str]]] = {
        Phase.NUCLEO: (
            ["ste.signal.momentum", "ste.regime.hurst", "ste.risk.policy"],
            [
                "Mantener cobertura de tests en señal/regimen/riesgo",
                "Consolidar reglas de halt y sizing en PolicyConfig",
            ],
        ),
        Phase.INGESTA_ESQUEMA: (
            ["ste.ingest.parquet_store", "ste.ingest.yfinance_bars"],
            [
                "Fijar rutas reproducibles de ingesta a Parquet",
                "Agregar validaciones de schema/metadata en CI",
            ],
        ),
        Phase.EVALUACION: (
            ["ste.eval.walkforward", "ste.eval.paper_replay"],
            [
                "Definir benchmark mínimo de walk-forward",
                "Añadir costes/slippage en replay para shadow",
            ],
        ),
        Phase.ORQUESTACION_PAPER: (
            ["ste.orchestration.app", "ste.diagnostics.check"],
            [
                "Conectar health/check/phase-status en una vista operativa",
                "Automatizar corridas paper por scheduler",
            ],
        ),
        Phase.LIVE_MIN: (
            ["ste.execution.mt5_driver", "MetaTrader5"],
            [
                "Validar adapter MT5 en entorno Windows con micro-lotes",
                "Probar kill switch operativo end-to-end antes de capital real",
            ],
        ),
    }
    checklist = _load_phase_checklist()
    for ph in Phase:
        evidence, next_actions = checks[ph]
        ov = checklist.get(int(ph), {})
        if isinstance(ov.get("evidence"), list):
            evidence = [str(x) for x in ov["evidence"]]
        completed_actions: list[str] = []
        if isinstance(ov.get("next_actions"), list):
            next_actions, completed_actions = _split_actions(ov["next_actions"])
        missing = [m for m in evidence if not _has(m)]
        ready = not missing
        action_progress = {
            "pending": len(next_actions),
            "completed": len(completed_actions),
            "total": len(next_actions) + len(completed_actions),
        }
        statuses.append(
            PhaseStatus(
                phase=int(ph),
                name=ph.name,
                description=desc[ph],
                ready=ready,
                evidence=evidence,
                missing=missing,
                next_actions=next_actions,
                completed_actions=completed_actions,
                action_progress=action_progress,
            )
        )
    return statuses


def phase_progress_report() -> dict[str, Any]:
    statuses = assess_phase_statuses()
    highest_ready = -1
    for st in statuses:
        if st.ready:
            highest_ready = st.phase
        else:
            break
    next_phase = highest_ready + 1 if highest_ready < int(Phase.LIVE_MIN) else None
    blocked_by: list[str] = []
    if next_phase is not None:
        blocked = next((s for s in statuses if s.phase == next_phase), None)
        if blocked:
            blocked_by = blocked.missing
    next_actions: list[str] = []
    for st in statuses:
        if not st.ready:
            next_actions = st.next_actions
            break
    return {
        "checklist_path": str(_checklist_path()),
        "highest_ready_phase": highest_ready,
        "next_phase": next_phase,
        "blocked_by": blocked_by,
        "next_actions": next_actions,
        "phases": [s.to_jsonable() for s in statuses],
    }
