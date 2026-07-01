from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Provider(str, Enum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OPENAI = "openai"
    CUSTOM = "custom"


@dataclass
class LLMResponse:
    command: str = ""
    explanation: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    error: Optional[str] = None
    raw: str = ""

    @classmethod
    def from_json(cls, raw: str) -> "LLMResponse":
        text = raw.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return cls(error=f"Failed to parse LLM response as JSON", raw=raw)
        try:
            risk = RiskLevel(data.get("risk_level", "low"))
        except ValueError:
            risk = RiskLevel.LOW
        return cls(
            command=data.get("command", ""),
            explanation=data.get("explanation", ""),
            risk_level=risk,
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            error=data.get("error"),
            raw=raw,
        )


@dataclass
class LLMConfig:
    provider: Provider = Provider.OLLAMA
    model: str = "llama3"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    temperature: float = 0.1
    max_tokens: int = 500
    timeout: int = 30


@dataclass
class SafetyConfig:
    require_confirmation: list[RiskLevel] = field(
        default_factory=lambda: [RiskLevel.HIGH, RiskLevel.CRITICAL]
    )
    blocked_commands: list[str] = field(default_factory=list)


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    dry_run: bool = False
    auto_confirm: bool = False
    no_stream: bool = False
