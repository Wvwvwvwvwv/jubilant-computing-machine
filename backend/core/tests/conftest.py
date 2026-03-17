"""Test compatibility helpers for mixed Starlette/httpx versions."""

from __future__ import annotations

import inspect

import httpx


_ORIGINAL_HTTPX_CLIENT_INIT = httpx.Client.__init__


def _patch_httpx_client_init_for_starlette_testclient() -> None:
    """Allow Starlette TestClient(app=...) with httpx versions that dropped `app` kwarg."""

    signature = inspect.signature(httpx.Client.__init__)
    if "app" in signature.parameters:
        return

    def _compat_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _ORIGINAL_HTTPX_CLIENT_INIT(self, *args, **kwargs)

    httpx.Client.__init__ = _compat_init  # type: ignore[assignment]


_patch_httpx_client_init_for_starlette_testclient()
