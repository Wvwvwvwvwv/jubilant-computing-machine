import json
import re
from dataclasses import dataclass

from backend.core.services.kobold_client import KoboldClient


@dataclass
class TaskExecutionPlan:
    tool: str
    language: str
    code: str
    timeout: int = 30


class TaskPlanner:
    """Planner with LLM-first routing and deterministic fallback heuristics."""

    PREFIX_TO_LANGUAGE = {
        "bash:": "bash",
        "sh:": "bash",
        "python:": "python",
        "py:": "python",
        "javascript:": "javascript",
        "js:": "javascript",
    }

    def __init__(self):
        self.kobold = KoboldClient()

    def _infer_language(self, goal: str) -> str:
        lowered = goal.lower()

        # Explicit prefix has priority.
        for prefix, language in self.PREFIX_TO_LANGUAGE.items():
            if lowered.startswith(prefix):
                return language

        # Intent-based fallback.
        python_markers = ["print(", "import ", "def ", "for ", "while ", "python "]
        js_markers = ["console.log", "const ", "let ", "function ", "javascript ", "node "]

        if any(marker in lowered for marker in python_markers):
            return "python"
        if any(marker in lowered for marker in js_markers):
            return "javascript"
        return "bash"

    def _strip_prefix(self, goal: str, language: str) -> str:
        lowered = goal.lower().strip()
        for prefix, pref_lang in self.PREFIX_TO_LANGUAGE.items():
            if pref_lang == language and lowered.startswith(prefix):
                return goal[len(prefix):].strip()
        return goal.strip()

    def _heuristic_plan(self, goal: str) -> TaskExecutionPlan:
        raw_goal = (goal or "").strip()
        language = self._infer_language(raw_goal)
        code = self._strip_prefix(raw_goal, language)
        return TaskExecutionPlan(tool="sandbox.execute", language=language, code=code, timeout=30)

    def _extract_json(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("empty llm output")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("json payload not found")
        return json.loads(match.group(0))

    async def build_plan(self, goal: str) -> TaskExecutionPlan:
        raw_goal = (goal or "").strip()
        if not raw_goal:
            return self._heuristic_plan(goal)

        prompt = (
            "You are a task planner for a sandbox executor. "
            "Return ONLY valid JSON with keys: tool, language, code, timeout. "
            "tool must be sandbox.execute. language must be one of python/javascript/bash. "
            "timeout must be integer 1..120. code must contain runnable code only."
        )

        try:
            output = await self.kobold.generate(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Goal:\n{raw_goal}"},
                ],
                max_tokens=220,
                temperature=0.0,
                top_p=0.9,
            )
            payload = self._extract_json(output)
            language = str(payload.get("language", "")).strip().lower()
            if language not in {"python", "javascript", "bash"}:
                raise ValueError(f"unsupported language: {language}")
            tool = str(payload.get("tool", "sandbox.execute")).strip() or "sandbox.execute"
            if tool != "sandbox.execute":
                tool = "sandbox.execute"
            code = str(payload.get("code", "")).strip()
            if not code:
                raise ValueError("empty code")
            timeout_raw = int(payload.get("timeout", 30))
            timeout = max(1, min(120, timeout_raw))
            return TaskExecutionPlan(tool=tool, language=language, code=code, timeout=timeout)
        except Exception:
            return self._heuristic_plan(raw_goal)
