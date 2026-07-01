from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

from .models import RiskLevel


_CRITICAL_PATTERNS = [
    re.compile(r) for r in [
        r'\b(reboot|shutdown|poweroff|halt|init\s+[06])\b',
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
        r'\brm\s+(-rf\b|--recursive|-[a-z]*r[a-z]*\s+)',
        r'\brm\s+(-[a-z]*f[a-z]*\s+[^\s])',
        r'\bkill\s+',
        r'\bpkill\s+',
        r'\bkillall\s+',
        r'\bchmod\s+',
        r'\bchown\s+',
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
        r'\bmkdir\s+',
        r'\btouch\s+',
        r'\bcp\s+',
        r'\bmv\s+',
        r'\brm\s+',
        r'\b(nano|vim?|emacs|code)\s+',
        r'\bcurl\s+',
        r'\bwget\s+',
        r'\btar\s+',
        r'\b(gzip|gunzip|zip|unzip)\s+',
        r'\b(pip|npm|apt(-get)?|brew|pacman)\s+(install|uninstall|update|upgrade)\b',
        r'\bmake\b',
        r'\bcmake\b',
        r'\bcargo\b',
        r'\bpython[23]?\s+\S+\.py',
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
        if not blocked:
            continue
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
    if command.strip().lower() in ("cls", "clear"):
        os.system("cls" if os.name == "nt" else "clear")
        return subprocess.CompletedProcess(command, 0, "", "")
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
