"""
`ste check`: versión de Python, paquetes críticos y *opcionales* (yfinance, etc.).
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# Perfiles predefinidos para `ste check --profile …` (CI / entornos).
CHECK_PROFILES: dict[str, tuple[str, ...]] = {
    "api": ("fastapi", "uvicorn", "httpx"),
    "fetch": ("yfinance",),
    "dev": ("pytest", "ruff"),
}
CHECK_ALL_PROFILE = "all"


def merge_required_from_profile(
    profile: str | None,
    extra: Iterable[str],
) -> list[str]:
    """Módulos del perfil primero, luego *extra*, sin duplicados."""
    out: list[str] = []
    seen: set[str] = set()
    if profile:
        if profile == CHECK_ALL_PROFILE:
            for name in sorted(CHECK_PROFILES):
                for m in CHECK_PROFILES[name]:
                    if m not in seen:
                        seen.add(m)
                        out.append(m)
        else:
            for m in CHECK_PROFILES[profile]:
                if m not in seen:
                    seen.add(m)
                    out.append(m)
    for m in extra:
        ms = m.strip()
        if not ms or ms in seen:
            continue
        seen.add(ms)
        out.append(ms)
    return out


@dataclass
class CheckResult:
    ok: bool = True
    profile: str | None = None
    effective_required: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    core_missing: list[str] = field(default_factory=list)
    optional_missing: list[str] = field(default_factory=list)
    required_missing: list[str] = field(default_factory=list)
    failed_categories: list[str] = field(default_factory=list)
    status_code: int = 0

    def add(self, s: str) -> None:
        self.lines.append(s)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "profile": self.profile,
            "effective_required": self.effective_required,
            "lines": self.lines,
            "core_missing": self.core_missing,
            "optional_missing": self.optional_missing,
            "required_missing": self.required_missing,
            "failed_categories": self.failed_categories,
            "status_code": self.status_code,
        }

def _check_modules(targets: Iterable[str], missing: list[str], lines: list[str]) -> None:
    for name in targets:
        try:
            m = importlib.import_module(name)
            v = getattr(m, "__version__", "?")
            lines.append(f"{name}: {v}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"{name}: (no) {e!r}")
            missing.append(name)


def run_checks(
    required_modules: Iterable[str] = (),
    *,
    profile: str | None = None,
) -> CheckResult:
    r = CheckResult(profile=profile)
    r.add(f"python: {sys.version.split()[0]} ({sys.executable})")
    r.add(f"platform: {sys.platform}")
    _check_modules(("numpy", "pyarrow", "pydantic", "ste"), r.core_missing, r.lines)
    _check_modules(("yfinance", "fastapi", "uvicorn", "pandas"), r.optional_missing, r.lines)
    merged = merge_required_from_profile(profile, required_modules)
    r.effective_required = merged
    if profile:
        r.add(f"check_profile: {profile}")
    if merged:
        r.add(f"required_modules: {', '.join(merged)}")
        _check_modules(tuple(merged), r.required_missing, r.lines)
    r.ok = not r.core_missing and not r.required_missing
    return r
