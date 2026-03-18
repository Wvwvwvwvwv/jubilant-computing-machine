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


def test_task_planner_uses_safe_termux_pkg_plan_for_python_install(monkeypatch):
    planner = TaskPlanner()
    monkeypatch.setenv("ANDROID_ROOT", "/system")

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("LLM should not be used for guarded Termux Python install flow")

    monkeypatch.setattr(planner.kobold, "generate", fail_if_called)
    plan = asyncio.run(planner.build_plan("Зайди на сайт https://www.python.org/downloads/ и скачай и установи python 3,13"))
    assert plan.tool == "sandbox.execute"
    assert plan.language == "bash"
    assert "pkg install -y python" in plan.code
    assert "python.org/downloads" in plan.code
    assert "make altinstall" not in plan.code
    assert plan.timeout == 120
