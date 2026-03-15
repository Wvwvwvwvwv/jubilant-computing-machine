# Multimodal RAG Integration — Week 1

## Scope

Week 1 introduces a safe retrieval abstraction layer without breaking existing chat/memory flows.

## Delivered in Week 1

- Retrieval backend abstraction via `backend/core/services/retrieval.py`.
- `LegacyMemoryRetriever` adapter over existing `MemoryEngine`.
- Feature flag `MULTIMODAL_RAG_ENABLED` to switch retrieval backend in chat.
- Runtime hook `app.state.multimodal_retriever` for future RAG-Anything adapter injection.
- Chat context block now marks selected retrieval backend (`legacy` or `multimodal`).
- Companion response traces include `retrieval_backend` for explainability/audit.
- Retrieval API endpoints for Week 1: `GET /api/retrieval/health` and `POST /api/retrieval/search`.

## Rollout Contract

- Default behavior: `legacy` backend (no functional change expected).
- Multimodal path activates only when:
  1) `MULTIMODAL_RAG_ENABLED=1`, and
  2) `app.state.multimodal_retriever` is present and has async `search`.
- If multimodal is unavailable, chat falls back to legacy automatically.

## Next (Week 2)

- ✅ Add indexing jobs API (completed in Week 2).
- Implement first concrete multimodal retriever adapter.
- Add retrieval explainability fields to companion traces.
