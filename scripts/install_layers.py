"""
Instala `requirements/layers/01-*.txt` … `09-*.txt` en orden, y opcionalmente
`requirements/optional/*.txt` al final.

Uso (desde la raíz del repo):
  python scripts/install_layers.py
  python scripts/install_layers.py --dry-run
  python scripts/install_layers.py --continue   # no parar en el primer error
  python scripts/install_layers.py --include-optional
  python scripts/install_layers.py --log install-log.txt
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "requirements" / "layers"
OPTIONAL = ROOT / "requirements" / "optional"


def _files(dir_path: Path, pattern: str) -> list[Path]:
    if not dir_path.is_dir():
        return []
    return sorted(dir_path.glob(pattern))


def main() -> int:
    p = argparse.ArgumentParser(description="Instalación por capas (pip).")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprimir los comandos pip, sin ejecutar.",
    )
    p.add_argument(
        "--continue",
        action="store_true",
        dest="cont",
        help="Seguir con la siguiente capa si una falla.",
    )
    p.add_argument(
        "--include-optional",
        action="store_true",
        help=f"También instalar {OPTIONAL}/*.txt al final (TF, Ray, etc.).",
    )
    p.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Añadir salida a un archivo de registro (UTF-8).",
    )
    args = p.parse_args()

    layer_files = _files(LAYERS, "*.txt")
    if not layer_files:
        print("No se encontró requirements/layers/*.txt", file=sys.stderr)
        return 1

    optional_files = _files(OPTIONAL, "*.txt") if args.include_optional else []
    all_reqs: list[Path] = list(layer_files) + list(optional_files)

    log_lines: list[str] = []

    def out(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    out(f"# STE install_layers {datetime.now(timezone.utc).isoformat()}")
    out(f"# Python: {sys.version.split()[0]}")

    failed: list[str] = []
    for req in all_reqs:
        rel = req.relative_to(ROOT)
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req)]
        out(f"\n## {' '.join(cmd)}")
        if args.dry_run:
            continue
        r = subprocess.run(
            cmd,
            cwd=ROOT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            failed.append(str(rel))
            out(f"!! FALLO ({r.returncode}): {rel}")
            if not args.cont:
                out("\nParada en primer error. Revisar mensaje de pip, corregir o ajustar la capa, y re-ejecutar.")
                break
        else:
            out(f"OK: {rel}")

    if args.log:
        args.log.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        print(f"\n# Registro escrito: {args.log.resolve()}")

    if failed and not args.dry_run:
        out(f"\n# Capas con error: {failed}")
        return 1
    if args.dry_run:
        out(f"\n# (dry-run) {len(all_reqs)} archivos; ejecutar sin --dry-run para instalar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
