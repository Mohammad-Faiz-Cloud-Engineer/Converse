from __future__ import annotations

import os
import platform
from typing import Generator

from .models import LLMConfig, LLMResponse
from .llm import complete, stream_completion
from .prompt import SYSTEM_PROMPT


def _build_messages(query: str) -> list[dict]:
    cwd = os.getcwd()
    system = platform.system()
    user_content = (
        f"Current directory: {cwd}\n"
        f"Operating system: {system}\n\n"
        f"Natural language request: {query}\n\n"
        f"Translate this into a shell command and output only JSON."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def translate(
    query: str,
    config: LLMConfig,
    stream: bool = True,
) -> Generator[str, None, None]:
    """Translate a natural language query to a shell command.

    If stream=True, yields response tokens as they arrive.
    If stream=False, yields the complete response as a single token.
    """
    messages = _build_messages(query)

    if stream:
        for token in stream_completion(config, messages):
            yield token
    else:
        response = complete(config, messages)
        yield response


def parse_response(response_text: str) -> LLMResponse:
    """Parse the LLM response text into a structured LLMResponse."""
    text = response_text.strip()

    if "```json" in text:
        parts = text.split("```json", 1)
        text = parts[1].split("```", 1)[0].strip()
    elif "```" in text:
        parts = text.split("```", 1)
        if len(parts) > 1:
            text = parts[1].split("```", 1)[0].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return LLMResponse.from_json(text)
