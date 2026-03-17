from backend.core.services.kobold_client import KoboldClient, DEFAULT_SYSTEM_PROMPT


def test_kobold_prompt_injects_default_russian_system_prompt():
    client = KoboldClient()
    prompt = client._format_messages([
        {"role": "user", "content": "Привет"},
    ])

    assert prompt.startswith(f"System: {DEFAULT_SYSTEM_PROMPT}")
    assert "User: Привет" in prompt
    assert prompt.endswith("Assistant:")


def test_kobold_prompt_keeps_existing_system_messages_after_default():
    client = KoboldClient()
    prompt = client._format_messages([
        {"role": "system", "content": "Дополнительная политика"},
        {"role": "user", "content": "Hello"},
    ])

    lines = prompt.split("\n\n")
    assert lines[0] == f"System: {DEFAULT_SYSTEM_PROMPT}"
    assert lines[1] == "System: Дополнительная политика"
    assert "User: Hello" in prompt
