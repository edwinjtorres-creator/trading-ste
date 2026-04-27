"""
Persistencia reproducible: `Bar` → Parquet → `Bar` (mismo *schema* lógico).

*extra* se serializa como JSON para columnas sencillas (evitar estructuras no JSON).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

import pyarrow as pa
import pyarrow.parquet as pq

from ste.contracts import Bar

SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class IngestRunMeta:
    """Metadatos en el *footer* Parquet; versionable."""

    schema_version: str
    n_rows: int
    custom: dict[str, Any] = field(default_factory=dict)


def _dt_utc_to_ns(t: datetime) -> int:
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    else:
        t = t.astimezone(timezone.utc)
    return int(t.timestamp() * 1_000_000_000)


def _ns_utc_to_dt(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)


def _extra_to_str(extra: Mapping[str, Any] | None) -> str:
    if not extra:
        return "{}"
    return json.dumps(dict(extra), sort_keys=True, separators=(",", ":"), default=str)


def _extra_from_str(s: str | None) -> dict[str, Any]:
    if not s or s == "{}":
        return {}
    return json.loads(s)


def write_bars(
    path: str | Path,
    bars: Sequence[Bar],
    run_meta: Mapping[str, Any] | None = None,
) -> None:
    """Escribe *bars* (una fila = un bar, orden guardado) en un único Parquet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(bars)
    if n == 0:
        raise ValueError("no hay bares que escribir")
    ex = [_extra_to_str(b.extra) for b in bars]
    table = pa.table(
        {
            "symbol": [b.symbol for b in bars],
            "timeframe": [b.timeframe for b in bars],
            "open_time_utc_ns": pa.array(
                [_dt_utc_to_ns(b.open_time_utc) for b in bars], type=pa.int64()
            ),
            "open": [float(b.open) for b in bars],
            "high": [float(b.high) for b in bars],
            "low": [float(b.low) for b in bars],
            "close": [float(b.close) for b in bars],
            "volume": [float(b.volume) for b in bars],
            "extra_json": ex,
        }
    )
    meta: dict[bytes, bytes] = {
        b"ste.schema": SCHEMA_VERSION.encode("utf-8"),
        b"ste.n": str(n).encode("utf-8"),
    }
    if run_meta is not None:
        meta[b"ste.run"] = json.dumps(
            {**dict(run_meta), "schema_version": SCHEMA_VERSION, "n_rows": n},
            default=str,
        ).encode("utf-8")
    w = table.replace_schema_metadata(meta)
    pq.write_table(
        w,
        path,
        version="2.6",
        compression="zstd",
        use_dictionary=True,
    )


def read_bars(path: str | Path) -> list[Bar]:
    t = pq.read_table(Path(path))
    sm = t.schema.metadata or {}
    v = sm.get(b"ste.schema", b"1").decode("utf-8", errors="replace")
    if v != SCHEMA_VERSION:
        raise ValueError(f"versión de schema no soportada: {v!r} (esperado {SCHEMA_VERSION!r})")

    nrows = t.num_rows
    if nrows == 0:
        return []
    sym = t.column("symbol").to_pylist()
    tf = t.column("timeframe").to_pylist()
    ns = t.column("open_time_utc_ns").to_pylist()
    o = t.column("open").to_pylist()
    h = t.column("high").to_pylist()
    lo = t.column("low").to_pylist()
    c_ = t.column("close").to_pylist()
    v_ = t.column("volume").to_pylist()
    ex = t.column("extra_json").to_pylist()
    out: list[Bar] = []
    for i in range(nrows):
        extra = _extra_from_str(cast("str", ex[i]))
        out.append(
            Bar(
                symbol=str(sym[i]),
                timeframe=str(tf[i]),
                open_time_utc=_ns_utc_to_dt(int(ns[i])),
                open=float(o[i]),
                high=float(h[i]),
                low=float(lo[i]),
                close=float(c_[i]),
                volume=float(v_[i]),
                extra=extra,
            )
        )
    return out


def read_bars_metadata(path: str | Path) -> IngestRunMeta | None:
    """Metadatos *ste.run* sin cargar tablas (rápido para CI)."""
    p = Path(path)
    f = pq.ParquetFile(p)
    m = f.schema_arrow.metadata or {}
    r = m.get(b"ste.run")
    if not r:
        n = f.metadata.num_rows
        v = m.get(b"ste.schema", b"1").decode("utf-8", errors="replace")
        return IngestRunMeta(schema_version=v, n_rows=n, custom={})
    d = json.loads(r.decode("utf-8"))
    return IngestRunMeta(
        schema_version=d.get("schema_version", SCHEMA_VERSION),
        n_rows=int(d.get("n_rows", 0)),
        custom={k: v for k, v in d.items() if k not in ("schema_version", "n_rows")},
    )
