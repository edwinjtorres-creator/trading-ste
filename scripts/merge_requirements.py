"""
Une `requirements/layers/*.txt` en `requirements/all.txt` (sin comentarios;
deduplicación por nombre de paquete en minúsculas).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "requirements" / "layers"
OUT = ROOT / "requirements" / "all.txt"

# Primer token: torch, dask[complete], etc.
_NAME = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9_.-]*)(\[.*\])?")
_EXTRAS = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9_.-]*)(\[.+\])")


def package_key(line: str) -> str:
    s = line.strip()
    s = s.split(";", 1)[0].strip()
    s = s.split("#", 1)[0].strip()
    m = _EXTRAS.match(s) or _NAME.match(s)
    if not m:
        return s.lower()
    return m.group(1).lower()


def main() -> None:
    if not LAYERS.is_dir():
        raise SystemExit(f"Falta carpeta {LAYERS}")
    # No mezclar hojas *-optional-*.txt en *all*; instalar a mano si aplica (p. ej. TensorFlow+Python<3.13)
    files = sorted(
        f for f in LAYERS.glob("*.txt") if "optional" not in f.stem and "optional" not in f.name
    )
    seen: set[str] = set()
    out: list[str] = []
    for fp in files:
        for line in fp.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            k = package_key(raw)
            if k in seen:
                continue
            seen.add(k)
            out.append(raw)
    text = f"# Generado: merge de requirements/layers/ ({len(out)} paquetes unicos)\n" + "\n".join(out) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(OUT, len(out))


if __name__ == "__main__":
    main()
