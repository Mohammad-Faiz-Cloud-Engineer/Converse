from __future__ import annotations

import json
from typing import Generator

from .models import LLMConfig


def _build_headers(config: LLMConfig) -> dict:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _build_payload(config: LLMConfig, messages: list[dict], stream: bool) -> dict:
    return {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": stream,
    }


def stream_completion(
    config: LLMConfig,
    messages: list[dict],
) -> Generator[str, None, None]:
    """Stream a chat completion from the LLM provider."""
    try:
        import httpx
    except ImportError:
        yield "Error: The 'httpx' library is required. Install with: pip install httpx\n"
        return

    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = _build_headers(config)
    payload = _build_payload(config, messages, stream=True)

    try:
        with httpx.Client(timeout=config.timeout) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_body = response.read().decode()
                    yield f"Error: API returned status {response.status_code}\n{error_body}"
                    return

                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    except httpx.ConnectError:
        yield (
            f"Error: Could not connect to {config.base_url}\n"
            f"Make sure your {config.provider.value} server is running.\n"
            f"  Ollama:  ollama serve\n"
            f"  LM Studio: Start the app and enable the local API server\n"
        )
    except httpx.TimeoutException:
        yield f"Error: Request timed out after {config.timeout} seconds.\n"
    except Exception as e:
        yield f"Error: {e}\n"


def complete(config: LLMConfig, messages: list[dict]) -> str:
    """Get a complete (non-streaming) response from the LLM."""
    try:
        import httpx
    except ImportError:
        return "Error: The 'httpx' library is required. Install with: pip install httpx"

    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = _build_headers(config)
    payload = _build_payload(config, messages, stream=False)

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=config.timeout)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            return msg.get("content", "")
        return "Error: No response content from LLM."
    except httpx.HTTPStatusError as e:
        return f"Error: API returned {e.response.status_code}: {e.response.text}"
    except httpx.ConnectError:
        return (
            f"Error: Could not connect to {config.base_url}\n"
            f"Make sure your {config.provider.value} server is running."
        )
    except httpx.TimeoutException:
        return f"Error: Request timed out after {config.timeout} seconds."
    except Exception as e:
        return f"Error: {e}"
