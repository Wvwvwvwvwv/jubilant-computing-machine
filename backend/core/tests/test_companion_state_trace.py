from backend.core.services.companion_state import CompanionState


def test_set_last_trace_defaults_retrieval_backend_legacy():
    state = CompanionState()
    trace = state.set_last_trace(response_id="resp_1")
    assert trace.retrieval_backend == "legacy"


def test_set_last_trace_accepts_retrieval_backend_override():
    state = CompanionState()
    trace = state.set_last_trace(response_id="resp_2", retrieval_backend="multimodal")
    assert trace.retrieval_backend == "multimodal"
