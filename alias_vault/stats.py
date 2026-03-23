"""Usage analytics and shell hook generation for tracking alias usage."""

from __future__ import annotations

from typing import Any


def get_most_used(aliases: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Get most frequently used aliases."""
    used = [a for a in aliases if a.get("use_count", 0) > 0]
    used.sort(key=lambda x: x.get("use_count", 0), reverse=True)
    return used[:limit]


def get_least_used(aliases: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Get least used aliases (that have been used at least once)."""
    used = [a for a in aliases if a.get("use_count", 0) > 0]
    used.sort(key=lambda x: x.get("use_count", 0))
    return used[:limit]


def get_never_used(aliases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get aliases that have never been used."""
    return [a for a in aliases if a.get("use_count", 0) == 0]


def get_stats_summary(aliases: list[dict[str, Any]]) -> dict[str, Any]:
    """Get overall usage statistics."""
    total = len(aliases)
    total_uses = sum(a.get("use_count", 0) for a in aliases)
    used = sum(1 for a in aliases if a.get("use_count", 0) > 0)
    never_used = total - used

    # Group by shell
    by_shell: dict[str, int] = {}
    for a in aliases:
        shell = a.get("shell", "all")
        by_shell[shell] = by_shell.get(shell, 0) + 1

    # Group by tag
    by_tag: dict[str, int] = {}
    for a in aliases:
        tags = a.get("tags", "")
        if tags:
            for tag in tags.split(","):
                tag = tag.strip()
                if tag:
                    by_tag[tag] = by_tag.get(tag, 0) + 1

    return {
        "total_aliases": total,
        "total_uses": total_uses,
        "used_aliases": used,
        "never_used": never_used,
        "usage_rate": f"{used / total * 100:.1f}%" if total > 0 else "0%",
        "avg_uses": round(total_uses / used, 1) if used > 0 else 0,
        "by_shell": by_shell,
        "by_tag": dict(sorted(by_tag.items(), key=lambda x: -x[1])),
    }


def generate_tracking_hook(shell: str = "bash") -> str:
    """Generate a shell hook that tracks alias usage via alias-vault.

    This wraps each alias so that when it's executed, it also records
    usage back to the vault.
    """
    if shell == "fish":
        return (
            "# Add to ~/.config/fish/config.fish for alias usage tracking\n"
            "function __alias_vault_preexec --on-event fish_preexec\n"
            "    set -l cmd (string split ' ' $argv[1])[1]\n"
            "    if alias-vault list --quiet 2>/dev/null | grep -qw \"$cmd\"\n"
            "        alias-vault record-usage \"$cmd\" 2>/dev/null &\n"
            "    end\n"
            "end\n"
        )

    if shell == "zsh":
        return (
            "# Add to ~/.zshrc for alias usage tracking\n"
            "__alias_vault_preexec() {\n"
            '    local cmd="${1%% *}"\n'
            '    if alias-vault list --quiet 2>/dev/null | grep -qw "$cmd"; then\n'
            '        alias-vault record-usage "$cmd" 2>/dev/null &\n'
            "    fi\n"
            "}\n"
            "autoload -Uz add-zsh-hook\n"
            "add-zsh-hook preexec __alias_vault_preexec\n"
        )

    # Bash
    return (
        "# Add to ~/.bashrc for alias usage tracking\n"
        "# Requires bash >= 4.0 with DEBUG trap\n"
        "__alias_vault_preexec() {\n"
        '    local cmd="${BASH_COMMAND%% *}"\n'
        '    if alias-vault list --quiet 2>/dev/null | grep -qw "$cmd"; then\n'
        '        alias-vault record-usage "$cmd" 2>/dev/null &\n'
        "    fi\n"
        "}\n"
        'trap "__alias_vault_preexec" DEBUG\n'
    )


def suggest_aliases(
    history_commands: list[str],
    existing_aliases: list[dict[str, Any]],
    min_length: int = 15,
    min_count: int = 3,
) -> list[dict[str, str]]:
    """Suggest new aliases based on command history.

    Analyzes frequent long commands that don't already have aliases.
    """
    existing_cmds = {a["command"] for a in existing_aliases}
    existing_names = {a["name"] for a in existing_aliases}

    # Count command frequencies
    cmd_counts: dict[str, int] = {}
    for cmd in history_commands:
        cmd = cmd.strip()
        if len(cmd) >= min_length and cmd not in existing_cmds:
            cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1

    # Filter by minimum count and sort by frequency
    frequent = sorted(
        [(cmd, count) for cmd, count in cmd_counts.items() if count >= min_count],
        key=lambda x: -x[1],
    )

    suggestions = []
    for cmd, count in frequent[:20]:
        # Generate a suggested name from the command
        parts = cmd.split()
        if len(parts) >= 2:
            name = parts[0][:2] + parts[1][:2]
        else:
            name = parts[0][:4]
        name = name.lower().replace("-", "").replace("/", "")

        # Ensure unique name
        base_name = name
        counter = 1
        while name in existing_names:
            name = f"{base_name}{counter}"
            counter += 1

        suggestions.append({
            "suggested_name": name,
            "command": cmd,
            "frequency": str(count),
        })
        existing_names.add(name)

    return suggestions
