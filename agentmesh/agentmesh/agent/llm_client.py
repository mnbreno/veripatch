"""OpenAI-compatible chat client for local LLM servers (LM Studio, etc.)."""

from __future__ import annotations

import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse JSON from raw LLM output, including markdown code fences."""
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, re.IGNORECASE)
    if fence:
        parsed = json.loads(fence.group(1).strip())
        if isinstance(parsed, dict):
            return parsed

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(stripped[start : end + 1])
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("LLM response did not contain a JSON object")


def chat_completions_sync(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    api_key: str = "lm-studio",
    timeout: float = 120.0,
    temperature: float = 0.2,
) -> str:
    """POST to /chat/completions and return assistant message content."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM connection failed: {exc.reason}") from exc

    choices = data.get("choices")
    if not choices:
        raise RuntimeError("LLM response missing choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content or not str(content).strip():
        raise RuntimeError("LLM response missing message content")
    return str(content)


async def chat_completions(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    api_key: str | None = None,
    timeout: float | None = None,
    temperature: float | None = None,
) -> str:
    """Async wrapper around the sync HTTP client."""
    return await asyncio.to_thread(
        chat_completions_sync,
        base_url=base_url,
        model=model,
        messages=messages,
        api_key=api_key or os.environ.get("AGENTMESH_LLM_API_KEY", "lm-studio"),
        timeout=timeout
        if timeout is not None
        else float(os.environ.get("AGENTMESH_LLM_TIMEOUT", "300")),
        temperature=temperature
        if temperature is not None
        else float(os.environ.get("AGENTMESH_LLM_TEMPERATURE", "0.2")),
    )
