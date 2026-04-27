import json

import ste.pipeline.phases as phases_mod
from ste.pipeline.phases import Phase, assess_phase_statuses, phase_progress_report


def test_assess_phase_statuses_shape() -> None:
    sts = assess_phase_statuses()
    assert len(sts) == 5
    assert [s.phase for s in sts] == [int(p) for p in Phase]
    assert all(isinstance(s.missing, list) for s in sts)
    assert all(isinstance(s.next_actions, list) for s in sts)
    assert all(isinstance(s.completed_actions, list) for s in sts)
    assert all(isinstance(s.action_progress, dict) for s in sts)


def test_phase_progress_report_keys() -> None:
    rep = phase_progress_report()
    assert "checklist_path" in rep
    assert "highest_ready_phase" in rep
    assert "next_phase" in rep
    assert "blocked_by" in rep
    assert "next_actions" in rep
    assert "phases" in rep
    assert isinstance(rep["phases"], list)
    assert len(rep["phases"]) == 5


def test_phase_status_uses_checklist_override() -> None:
    sts = assess_phase_statuses()
    p0 = next(s for s in sts if s.phase == int(Phase.NUCLEO))
    assert any("PolicyConfig" in a for a in p0.next_actions)
    assert p0.action_progress["total"] >= 1


def test_set_phase_action_done_roundtrip(tmp_path) -> None:
    p = tmp_path / "PHASES_CHECKLIST.json"
    p.write_text(
        json.dumps({"0": {"next_actions": [{"text": "a", "done": False}]}}),
        encoding="utf-8",
    )
    old = phases_mod._checklist_path
    phases_mod._checklist_path = lambda: p
    try:
        assert phases_mod.set_phase_action_done(0, "a", True) is True
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert raw["0"]["next_actions"][0]["done"] is True
    finally:
        phases_mod._checklist_path = old
