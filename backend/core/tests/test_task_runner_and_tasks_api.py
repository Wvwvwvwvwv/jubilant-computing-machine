from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import tasks as tasks_router
from backend.core.services.task_planner import TaskExecutionPlan
from backend.core.services.task_runner import TaskRunner


def make_runner(tmp_path) -> TaskRunner:
    runner = TaskRunner()
    runner.log_path = tmp_path / "task_audit.log"
    runner.state_path = tmp_path / "tasks_state.json"
    runner.db_path = tmp_path / "tasks.db"
    runner._init_db()
    runner.tasks = {}
    return runner


def make_client(tmp_path) -> tuple[TestClient, TaskRunner]:
    app = FastAPI()
    app.include_router(tasks_router.router, prefix="/api/tasks")
    runner = make_runner(tmp_path)
    app.state.task_runner = runner
    return TestClient(app), runner


def test_tasks_run_uses_planner_language_and_started_payload(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path)

    async def fake_build_plan(goal: str):
        assert goal == "python: print(2+2)"
        return TaskExecutionPlan(tool="sandbox.execute", language="python", code="print(2+2)", timeout=30)

    monkeypatch.setattr(tasks_router.planner, "build_plan", fake_build_plan)

    async def fake_execute_code(request):
        assert request.language == "python"
        assert request.code == "print(2+2)"
        return SimpleNamespace(exit_code=0, stdout="4\n", stderr="")

    monkeypatch.setattr(tasks_router, "execute_code", fake_execute_code)

    created = client.post(
        "/api/tasks/",
        json={"goal": "python: print(2+2)", "max_attempts": 2, "approval_required": False},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    ran = client.post(f"/api/tasks/{task_id}/run")
    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "SUCCESS"

    started_events = [e for e in body["events"] if e["kind"] == "task_started"]
    assert started_events
    last_started = started_events[-1]
    assert last_started["payload"]["tool"] == "sandbox.execute"
    assert last_started["payload"]["language"] == "python"


def test_high_risk_requires_approval_and_blocks_then_approves(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path)

    async def fake_build_plan(_goal: str):
        return TaskExecutionPlan(tool="sandbox.execute", language="bash", code="echo ok", timeout=30)

    monkeypatch.setattr(tasks_router.planner, "build_plan", fake_build_plan)

    async def fake_execute_code(_request):
        return SimpleNamespace(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(tasks_router, "execute_code", fake_execute_code)

    created = client.post(
        "/api/tasks/",
        json={"goal": "rm -rf /tmp/demo", "max_attempts": 2, "approval_required": False},
    ).json()

    assert created["status"] == "NEEDS_APPROVAL"
    task_id = created["task_id"]

    blocked = client.post(f"/api/tasks/{task_id}/run").json()
    assert blocked["status"] == "NEEDS_APPROVAL"
    assert any(e["kind"] == "task_blocked" for e in blocked["events"])

    approved = client.post(f"/api/tasks/{task_id}/approve").json()
    assert approved["approved"] is True
    assert any(e["kind"] == "task_approved" for e in approved["events"])

    ran = client.post(f"/api/tasks/{task_id}/run").json()
    assert ran["status"] == "SUCCESS"


def test_retry_policy_transient_vs_command_fail_fast(tmp_path):
    runner = make_runner(tmp_path)

    transient = runner.create_task("echo transient", max_attempts=3)
    runner.run_with_result(transient.task_id, exit_code=124, stderr="timed out")
    t_rec = runner.get_task(transient.task_id)
    assert t_rec is not None
    assert t_rec.status.value == "RETRYING"
    t_last = t_rec.events[-1]
    assert t_last.kind == "task_retry"
    assert t_last.payload["retry_allowed"] is True
    assert t_last.payload["retry_delay_seconds"] >= 2

    command = runner.create_task("badcmd", max_attempts=3)
    runner.run_with_result(command.task_id, exit_code=127, stderr="not found")
    c_rec = runner.get_task(command.task_id)
    assert c_rec is not None
    assert c_rec.status.value == "FAILED"
    c_last = c_rec.events[-1]
    assert c_last.kind == "task_failed"
    assert c_last.payload["retry_allowed"] is False


def test_approval_fingerprint_invalidates_stale_approval(tmp_path):
    runner = make_runner(tmp_path)
    rec = runner.create_task("rm -rf /tmp/demo", max_attempts=2)
    assert rec.approval_required is True

    runner.approve_task(rec.task_id)
    approved = runner.get_task(rec.task_id)
    assert approved is not None
    assert approved.approved is True

    approved.goal = "rm -rf /tmp/demo_changed"
    runner.run_with_result(approved.task_id, exit_code=0, stdout="ok")

    invalidated = runner.get_task(approved.task_id)
    assert invalidated is not None
    assert invalidated.status.value == "NEEDS_APPROVAL"
    assert invalidated.approved is False
    assert any(e.kind == "task_approval_invalidated" for e in invalidated.events)


def test_db_drift_is_seen_and_invalidation_triggers(tmp_path):
    runner = make_runner(tmp_path)
    rec = runner.create_task("rm -rf /tmp/demo", max_attempts=2)
    runner.approve_task(rec.task_id)

    with runner._db() as conn:
        conn.execute(
            "update tasks set goal=? where task_id=?",
            ("rm -rf /tmp/demo_drifted", rec.task_id),
        )

    refreshed = runner.get_task(rec.task_id)
    assert refreshed is not None
    assert refreshed.goal == "rm -rf /tmp/demo_drifted"

    updated = runner.run_with_result(rec.task_id, exit_code=0, stdout="ok")
    assert updated.status.value == "NEEDS_APPROVAL"
    assert updated.approved is False
    assert any(e.kind == "task_approval_invalidated" for e in updated.events)


def test_task_planner_heuristic_python_without_prefix(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path)

    async def fake_build_plan(goal: str):
        assert goal == "print(40+2)"
        return TaskExecutionPlan(tool="sandbox.execute", language="python", code="print(40+2)", timeout=30)

    monkeypatch.setattr(tasks_router.planner, "build_plan", fake_build_plan)

    async def fake_execute_code(request):
        assert request.language == "python"
        assert request.code == "print(40+2)"
        return SimpleNamespace(exit_code=0, stdout="42\n", stderr="")

    monkeypatch.setattr(tasks_router, "execute_code", fake_execute_code)

    created = client.post(
        "/api/tasks/",
        json={"goal": "print(40+2)", "max_attempts": 2, "approval_required": False},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    ran = client.post(f"/api/tasks/{task_id}/run")
    assert ran.status_code == 200
    body = ran.json()
    started_events = [e for e in body["events"] if e["kind"] == "task_started"]
    assert started_events[-1]["payload"]["language"] == "python"
