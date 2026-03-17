from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import httpx


ONLINE_TIMEOUT_SECONDS = float(os.getenv("ONLINE_HTTP_TIMEOUT_SECONDS", "20"))
DOWNLOADS_DIR = Path(os.getenv("ONLINE_DOWNLOADS_DIR", str(Path.home() / "roampal-android" / "downloads")))


def online_tools_enabled() -> bool:
    return os.getenv("ENABLE_ONLINE_TOOLS", "0").strip().lower() in {"1", "true", "yes", "on"}


async def web_search(query: str, limit: int = 5) -> list[dict]:
    q = quote_plus(query.strip())
    url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"

    async with httpx.AsyncClient(timeout=ONLINE_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    items: list[dict] = []
    abstract = (data.get("AbstractText") or "").strip()
    abstract_url = (data.get("AbstractURL") or "").strip()
    if abstract:
        items.append({"title": "DuckDuckGo Abstract", "snippet": abstract[:700], "url": abstract_url})

    for topic in data.get("RelatedTopics", []):
        if len(items) >= limit:
            break
        if isinstance(topic, dict) and "Text" in topic:
            items.append(
                {
                    "title": "Related",
                    "snippet": str(topic.get("Text", ""))[:700],
                    "url": str(topic.get("FirstURL", "")),
                }
            )
        elif isinstance(topic, dict) and "Topics" in topic:
            for nested in topic.get("Topics", []):
                if len(items) >= limit:
                    break
                if isinstance(nested, dict) and "Text" in nested:
                    items.append(
                        {
                            "title": "Related",
                            "snippet": str(nested.get("Text", ""))[:700],
                            "url": str(nested.get("FirstURL", "")),
                        }
                    )

    return items[:limit]


async def download_to_local(url: str, filename: str | None = None) -> dict:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    resolved = filename.strip() if filename else url.rstrip("/").split("/")[-1] or "download.bin"
    destination = DOWNLOADS_DIR / resolved

    async with httpx.AsyncClient(timeout=ONLINE_TIMEOUT_SECONDS) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        data = response.content

    destination.write_bytes(data)
    return {
        "path": str(destination),
        "size_bytes": len(data),
        "filename": resolved,
    }
