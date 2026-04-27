import numpy as np
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ste.contracts import Bar
from ste.ingest.parquet_store import write_bars


def test_build_app_needs_fastapi() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    app = build_app()
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_post_replay_v1(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    c = 100.0 + 0.1 * np.random.default_rng(0).standard_normal(40)
    bars: list[Bar] = []
    for i, cl in enumerate(c):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        hi = max(o, float(cl)) * 1.001
        lo = min(o, float(cl)) * 0.999
        bars.append(Bar("API", "1d", d, o, hi, lo, float(cl), 1.0, {}))
    p = tmp_path / "z.parquet"
    write_bars(p, bars, run_meta={})
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    c = TestClient(build_app())
    r = c.post(
        "/v1/replay",
        json={"file_path": p.as_posix(), "position_size": 0.2, "ignore_regime": True},
    )
    assert r.status_code == 200
    d = r.json()
    assert "equity_final" in d
    assert "bar_times" in d
    assert "total_cost_frac" in d
    assert "gate_passed" in d
    assert "gate_failures" in d


def test_openapi_includes_replay() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    spec = TestClient(build_app()).get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert "/v1/replay" in paths
    assert "/v1/eval-gate" in paths
    post = paths["/v1/replay"]["post"]
    assert "requestBody" in post
    ref = post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("/ReplayResponse")
    r400 = post["responses"]["400"]["content"]["application/json"]["schema"]["$ref"]
    r404 = post["responses"]["404"]["content"]["application/json"]["schema"]["$ref"]
    assert r400.endswith("/HttpErrorPlain")
    assert r404.endswith("/HttpErrorPlain")
    gate_post = paths["/v1/eval-gate"]["post"]
    gate_ref = gate_post["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert gate_ref.endswith("/EvalGateResponse")


def test_post_replay_v1_validation_422_slow_not_gt_fast(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    p = tmp_path / "x.parquet"
    p.write_text("x", encoding="utf-8")
    r = TestClient(build_app()).post(
        "/v1/replay",
        json={"file_path": p.as_posix(), "fast": 10, "slow": 5, "ignore_regime": True},
    )
    assert r.status_code == 422


def test_post_replay_v1_validation_422_position_size(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    p = tmp_path / "y.parquet"
    p.write_text("y", encoding="utf-8")
    r = TestClient(build_app()).post(
        "/v1/replay",
        json={"file_path": p.as_posix(), "position_size": 1.5, "ignore_regime": True},
    )
    assert r.status_code == 422


def test_post_replay_v1_missing_file_404() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    missing = "/tmp/ste_replay_404_test.parquet"
    r = TestClient(build_app()).post("/v1/replay", json={"file_path": missing})
    assert r.status_code == 404
    assert missing in r.json()["detail"]


def test_post_replay_v1_corrupt_parquet_400(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    p = tmp_path / "corrupt.parquet"
    p.write_bytes(b"not a parquet file")
    r = TestClient(build_app()).post(
        "/v1/replay", json={"file_path": p.as_posix(), "ignore_regime": True}
    )
    assert r.status_code == 400
    assert "inválido" in r.json()["detail"] or "incompatible" in r.json()["detail"]


def test_post_replay_v1_wrong_columns_parquet_400(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    import pyarrow as pa
    import pyarrow.parquet as pq
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    p = tmp_path / "wrong_cols.parquet"
    pq.write_table(pa.table({"x": [1, 2]}), p)
    r = TestClient(build_app()).post(
        "/v1/replay", json={"file_path": p.as_posix(), "ignore_regime": True}
    )
    assert r.status_code == 400
    d = r.json()["detail"]
    assert "inválido" in d or "incompatible" in d


def test_post_replay_v1_unsupported_schema_version_400(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    import pyarrow as pa
    import pyarrow.parquet as pq
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    ns = int(t0.timestamp() * 1_000_000_000)
    table = pa.table(
        {
            "symbol": ["X"],
            "timeframe": ["1d"],
            "open_time_utc_ns": pa.array([ns], type=pa.int64()),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1.0],
            "extra_json": ["{}"],
        }
    )
    bad_meta = {b"ste.schema": b"99"}
    pq.write_table(table.replace_schema_metadata(bad_meta), tmp_path / "v99.parquet")
    p = tmp_path / "v99.parquet"
    r = TestClient(build_app()).post(
        "/v1/replay", json={"file_path": p.as_posix(), "ignore_regime": True}
    )
    assert r.status_code == 400
    assert "inválido" in r.json()["detail"] or "incompatible" in r.json()["detail"]


def test_post_replay_v1_gate_flags(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    c = 100.0 + 0.1 * np.random.default_rng(0).standard_normal(40)
    bars: list[Bar] = []
    for i, cl in enumerate(c):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        hi = max(o, float(cl)) * 1.001
        lo = min(o, float(cl)) * 0.999
        bars.append(Bar("API2", "1d", d, o, hi, lo, float(cl), 1.0, {}))
    p = tmp_path / "gate.parquet"
    write_bars(p, bars, run_meta={})
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    c = TestClient(build_app())
    r = c.post(
        "/v1/replay",
        json={
            "file_path": p.as_posix(),
            "position_size": 0.2,
            "ignore_regime": True,
            "min_sharpe": 99.0,
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["gate_passed"] is False
    assert len(d["gate_failures"]) >= 1


def test_post_eval_gate_v1(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    c = 100.0 + 0.1 * np.random.default_rng(2).standard_normal(50)
    bars: list[Bar] = []
    for i, cl in enumerate(c):
        d = t0 + timedelta(days=i)
        o = float(cl) * 0.999
        hi = max(o, float(cl)) * 1.001
        lo = min(o, float(cl)) * 0.999
        bars.append(Bar("APIG", "1d", d, o, hi, lo, float(cl), 1.0, {}))
    p = tmp_path / "eg.parquet"
    write_bars(p, bars, run_meta={})
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    c = TestClient(build_app())
    r = c.post(
        "/v1/eval-gate",
        json={
            "file_path": p.as_posix(),
            "ignore_regime": True,
            "min_sharpe": 99.0,
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["passed"] is False
    assert len(d["failures"]) >= 1
    assert "metrics" in d
    assert "equity_final" in d["metrics"]


def test_get_ops_status_v1() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from ste.orchestration.app import build_app

    r = TestClient(build_app()).get("/ops/status")
    assert r.status_code == 200
    d = r.json()
    assert "status" in d
    assert "health" in d
    assert "check" in d
    assert "phase_progress" in d
