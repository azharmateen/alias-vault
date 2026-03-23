"""Import aliases from shell configuration files."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def parse_bash_aliases(content: str) -> list[dict[str, Any]]:
    """Parse alias definitions from bash/zsh config content.

    Handles:
        alias name='command'
        alias name="command"
        alias name=command
    """
    aliases = []
    # Match alias definitions - handles single quotes, double quotes, and unquoted
    pattern = re.compile(
        r"""^[ \t]*alias\s+([a-zA-Z_][\w.-]*)=(?:'([^']*)'|"([^"]*)"|(\S+))""",
        re.MULTILINE,
    )

    for match in pattern.finditer(content):
        name = match.group(1)
        command = match.group(2) or match.group(3) or match.group(4) or ""
        aliases.append({
            "name": name,
            "command": command,
            "shell": "bash",
            "description": "",
            "tags": "imported",
        })

    return aliases


def parse_fish_aliases(content: str) -> list[dict[str, Any]]:
    """Parse alias/abbr definitions from fish config.

    Handles:
        alias name 'command'
        alias name "command"
        alias name=command
        abbr -a name command
    """
    aliases = []

    # Fish alias format: alias name 'command' or alias name "command"
    alias_pattern = re.compile(
        r"""^[ \t]*alias\s+([a-zA-Z_][\w.-]*)\s+(?:'([^']*)'|"([^"]*)")""",
        re.MULTILINE,
    )
    for match in alias_pattern.finditer(content):
        name = match.group(1)
        command = match.group(2) or match.group(3) or ""
        aliases.append({
            "name": name,
            "command": command,
            "shell": "fish",
            "description": "",
            "tags": "imported",
        })

    # Fish alias=command format
    alias_eq_pattern = re.compile(
        r"""^[ \t]*alias\s+([a-zA-Z_][\w.-]*)=(?:'([^']*)'|"([^"]*)"|(\S+))""",
        re.MULTILINE,
    )
    for match in alias_eq_pattern.finditer(content):
        name = match.group(1)
        command = match.group(2) or match.group(3) or match.group(4) or ""
        # Skip if already found
        if not any(a["name"] == name for a in aliases):
            aliases.append({
                "name": name,
                "command": command,
                "shell": "fish",
                "description": "",
                "tags": "imported",
            })

    # Fish abbreviation format: abbr -a name command
    abbr_pattern = re.compile(
        r"""^[ \t]*abbr\s+(?:-a\s+)?([a-zA-Z_][\w.-]*)\s+(.+)$""",
        re.MULTILINE,
    )
    for match in abbr_pattern.finditer(content):
        name = match.group(1)
        command = match.group(2).strip().strip("'\"")
        if not any(a["name"] == name for a in aliases):
            aliases.append({
                "name": name,
                "command": command,
                "shell": "fish",
                "description": "",
                "tags": "imported,abbreviation",
            })

    return aliases


def import_from_file(filepath: str) -> list[dict[str, Any]]:
    """Import aliases from a shell config file.

    Auto-detects shell type from filename.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")

    content = path.read_text(errors="ignore")
    name = path.name.lower()

    if "fish" in name or str(path).endswith(".fish"):
        return parse_fish_aliases(content)
    else:
        # Bash, Zsh, and compatible shells
        aliases = parse_bash_aliases(content)
        if "zsh" in name:
            for a in aliases:
                a["shell"] = "zsh"
        return aliases


def discover_shell_configs() -> list[str]:
    """Discover common shell configuration files in the user's home directory."""
    home = Path.home()
    candidates = [
        home / ".bashrc",
        home / ".bash_profile",
        home / ".bash_aliases",
        home / ".zshrc",
        home / ".zsh_aliases",
        home / ".config" / "fish" / "config.fish",
        home / ".aliases",
        home / ".shell_aliases",
    ]
    return [str(p) for p in candidates if p.is_file()]


def import_all_discovered() -> list[dict[str, Any]]:
    """Import aliases from all discovered shell config files."""
    all_aliases: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for filepath in discover_shell_configs():
        try:
            aliases = import_from_file(filepath)
            for alias in aliases:
                if alias["name"] not in seen_names:
                    alias["tags"] = f"imported,{Path(filepath).name}"
                    all_aliases.append(alias)
                    seen_names.add(alias["name"])
        except (OSError, ValueError):
            continue

    return all_aliases
