"""Export aliases to various shell formats and data formats."""

from __future__ import annotations

import json
from typing import Any


def to_bash(aliases: list[dict[str, Any]]) -> str:
    """Export aliases to bash format."""
    lines = ["# Aliases exported by Alias Vault", ""]
    for alias in aliases:
        if alias.get("description"):
            lines.append(f"# {alias['description']}")
        cmd = alias["command"]
        # Use single quotes unless command contains them
        if "'" not in cmd:
            lines.append(f"alias {alias['name']}='{cmd}'")
        else:
            # Escape double quotes and use double quotes
            escaped = cmd.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'alias {alias["name"]}="{escaped}"')
    lines.append("")
    return "\n".join(lines)


def to_zsh(aliases: list[dict[str, Any]]) -> str:
    """Export aliases to zsh format (same as bash for basic aliases)."""
    return to_bash(aliases)


def to_fish(aliases: list[dict[str, Any]]) -> str:
    """Export aliases to fish shell format."""
    lines = ["# Aliases exported by Alias Vault", ""]
    for alias in aliases:
        if alias.get("description"):
            lines.append(f"# {alias['description']}")
        cmd = alias["command"]
        # Fish uses different quoting
        if "'" not in cmd:
            lines.append(f"alias {alias['name']} '{cmd}'")
        else:
            escaped = cmd.replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"alias {alias['name']} '{escaped}'")
    lines.append("")
    return "\n".join(lines)


def to_json(aliases: list[dict[str, Any]], pretty: bool = True) -> str:
    """Export aliases to JSON format."""
    export_data = []
    for alias in aliases:
        export_data.append({
            "name": alias["name"],
            "command": alias["command"],
            "description": alias.get("description", ""),
            "tags": alias.get("tags", ""),
            "shell": alias.get("shell", "all"),
        })
    if pretty:
        return json.dumps(export_data, indent=2)
    return json.dumps(export_data)


def to_yaml(aliases: list[dict[str, Any]]) -> str:
    """Export aliases to YAML format (no external dependency)."""
    lines = ["# Aliases exported by Alias Vault", "aliases:"]
    for alias in aliases:
        lines.append(f"  - name: {alias['name']}")
        # Quote commands that contain special YAML characters
        cmd = alias["command"]
        if any(c in cmd for c in ":#{}[]&*!|>'\"%@`"):
            lines.append(f'    command: "{cmd}"')
        else:
            lines.append(f"    command: {cmd}")
        if alias.get("description"):
            lines.append(f"    description: {alias['description']}")
        if alias.get("tags"):
            lines.append(f"    tags: {alias['tags']}")
        if alias.get("shell", "all") != "all":
            lines.append(f"    shell: {alias['shell']}")
    return "\n".join(lines)


def generate_source_snippet(vault_path: str, shell: str = "bash") -> str:
    """Generate a shell snippet that sources aliases from alias-vault.

    This generates a shell function and source line that can be added
    to .bashrc/.zshrc to auto-load aliases from the vault.
    """
    if shell == "fish":
        return (
            "# Add to ~/.config/fish/config.fish\n"
            f"# alias-vault export --format fish | source\n"
            f"if command -q alias-vault\n"
            f"    alias-vault export --format fish | source\n"
            f"end\n"
        )

    # Bash/Zsh
    return (
        f"# Add to ~/.{shell}rc\n"
        f"if command -v alias-vault &>/dev/null; then\n"
        f"    eval \"$(alias-vault export --format {shell})\"\n"
        f"fi\n"
    )


def export_aliases(
    aliases: list[dict[str, Any]],
    fmt: str = "bash",
) -> str:
    """Export aliases to specified format.

    Supported formats: bash, zsh, fish, json, yaml
    """
    exporters = {
        "bash": to_bash,
        "zsh": to_zsh,
        "fish": to_fish,
        "json": to_json,
        "yaml": to_yaml,
    }

    exporter = exporters.get(fmt)
    if exporter is None:
        raise ValueError(f"Unknown format: {fmt}. Supported: {', '.join(exporters)}")

    return exporter(aliases)
