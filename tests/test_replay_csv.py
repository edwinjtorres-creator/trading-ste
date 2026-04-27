from pathlib import Path

from ste.eval.paper_replay import write_replay_csv


def test_write_replay_csv(tmp_path: Path) -> None:
    r = {
        "bar_times": ["2020-01-01T00:00:00+00:00", "2020-01-02T00:00:00+00:00"],
        "returns": [0.01, -0.005],
        "equity_curve": [1.0, 1.01, 1.00495],
    }
    p = tmp_path / "e.csv"
    write_replay_csv(r, p)
    t = p.read_text(encoding="utf-8")
    assert "open_time_utc" in t
    assert "0.01" in t
