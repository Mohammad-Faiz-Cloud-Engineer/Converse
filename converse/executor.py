from __future__ import annotations

import re
import subprocess
from typing import Optional

from .models import RiskLevel


_CRITICAL_PATTERNS = [
    re.compile(r) for r in [
        r'^(reboot|shutdown|poweroff|halt|init\s+[06])\b',
        r'systemctl\s+(reboot|poweroff|halt|shutdown)',
        r'apt(-get)?\s+(remove|purge|autoremove)',
        r'dpkg\s+(-r\b|--remove|--purge)',
        r'rpm\s+-e\b',
        r'pacman\s+-R\s',
        r'dd\s+if=',
        r'mkfs\.',
        r'fdisk\s+',
        r'parted\s+',
    ]
]

_HIGH_PATTERNS = [
    re.compile(r) for r in [
        r'^rm\s+(-rf\b|--recursive|-[a-z]*r[a-z]*\s+)',
        r'^rm\s+(-[a-z]*f[a-z]*\s+[^\s])',
        r'^kill\s+',
        r'^pkill\s+',
        r'^killall\s+',
        r'^chmod\s+',
        r'^chown\s+',
        r'docker\s+(rm\b|rmi\b|system\s+prune)',
        r'git\s+reset\s+--hard',
        r'git\s+clean\s+-f[d]?',
        r'git\s+push\s+--force',
        r'>\s+/[a-z]',
        r'dd\s+of=',
    ]
]

_MEDIUM_PATTERNS = [
    re.compile(r) for r in [
        r'^mkdir\s+',
        r'^touch\s+',
        r'^cp\s+',
        r'^mv\s+',
        r'^rm\s+',
        r'^(nano|vim?|emacs|code)\s+',
        r'^curl\s+',
        r'^wget\s+',
        r'^tar\s+',
        r'^(gzip|gunzip|zip|unzip)\s+',
        r'^(pip|npm|apt(-get)?|brew|pacman)\s+(install|uninstall|update|upgrade)\b',
        r'^make\b',
        r'^cmake\b',
        r'^cargo\b',
        r'^python[23]?\s+\S+\.py',
    ]
]


def _strip_sudo(cmd: str) -> tuple[str, bool]:
    """Remove leading sudo invocation and return (stripped, had_sudo)."""
    m = re.match(r'^sudo\s+', cmd)
    if m:
        return cmd[m.end():], True
    return cmd, False


def determine_risk_level(command: str) -> RiskLevel:
    """Determine risk level by pattern-matching the command string."""
    if not command or not command.strip():
        return RiskLevel.LOW

    raw = command.strip()
    cmd, had_sudo = _strip_sudo(raw)

    for pattern in _CRITICAL_PATTERNS:
        if pattern.search(cmd):
            return RiskLevel.CRITICAL

    for pattern in _HIGH_PATTERNS:
        if pattern.search(cmd):
            return RiskLevel.HIGH

    for pattern in _MEDIUM_PATTERNS:
        if pattern.search(cmd):
            return RiskLevel.MEDIUM

    if had_sudo:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def check_blocked(command: str, blocked_list: list[str]) -> Optional[str]:
    """Check if the command contains any blocked commands.

    Uses word boundary anchors when the blocked pattern starts and ends with
    word characters to avoid false positives (e.g. 'rm' not matching 'mkdir').
    Falls back to substring matching for patterns with punctuation at edges
    where word boundaries are not meaningful.
    """
    cmd_lower = command.lower()
    for blocked in blocked_list:
        bl = blocked.lower()
        if bl[0].isalnum() and bl[-1].isalnum():
            if re.search(r'\b' + re.escape(bl) + r'\b', cmd_lower):
                return f"Command blocked by configuration: contains '{blocked}'"
        else:
            if bl in cmd_lower:
                return f"Command blocked by configuration: contains '{blocked}'"
    return None


def run_command(command: str) -> subprocess.CompletedProcess:
    """Execute a shell command and return the result."""
    return subprocess.run(
        command,
        shell=True,
        capture_output=False,
        text=True,
    )
