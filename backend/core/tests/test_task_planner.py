import asyncio

from backend.core.services.task_planner import TaskPlanner


def test_task_planner_uses_llm_json(monkeypatch):
    planner = TaskPlanner()

    async def fake_generate(*_args, **_kwargs):
        return '{"tool":"sandbox.execute","language":"javascript","code":"console.log(42)","timeout":22}'

    monkeypatch.setattr(planner.kobold, "generate", fake_generate)
    plan = asyncio.run(planner.build_plan("print 42"))
    assert plan.tool == "sandbox.execute"
    assert plan.language == "javascript"
    assert plan.code == "console.log(42)"
    assert plan.timeout == 22


def test_task_planner_falls_back_when_llm_fails(monkeypatch):
    planner = TaskPlanner()

    async def fail_generate(*_args, **_kwargs):
        raise RuntimeError("no llm")

    monkeypatch.setattr(planner.kobold, "generate", fail_generate)
    plan = asyncio.run(planner.build_plan("python: print(1)"))
    assert plan.language == "python"
    assert plan.code == "print(1)"
