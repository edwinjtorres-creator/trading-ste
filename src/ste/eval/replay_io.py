"""
Errores de lectura Parquet para *replay* compartidos entre CLI y API.
"""

from __future__ import annotations

import pyarrow as pa

# Código de salida `ste replay` cuando falla I/O o *schema* del Parquet.
CLI_REPLAY_IO_EXIT = 2

PARQUET_REPLAY_READ_ERRORS: tuple[type[BaseException], ...] = (
    ValueError,
    KeyError,
    pa.ArrowInvalid,
)


def parquet_not_found_message(exc: FileNotFoundError, path_fallback: str) -> str:
    path = exc.filename or path_fallback
    return f"Parquet no encontrado: {path}"


def parquet_invalid_message(exc: BaseException) -> str:
    return f"Parquet inválido o incompatible con STE: {exc}"
