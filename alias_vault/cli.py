"""Alias Vault CLI - Centralized shell alias manager."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .exporter import export_aliases, generate_source_snippet
from .importer import discover_shell_configs, import_from_file, import_all_discovered
from .search import search_aliases
from .stats import (
    generate_tracking_hook,
    get_most_used,
    get_never_used,
    get_stats_summary,
)
from .vault import Vault

console = Console()


def _get_vault(db: str | None = None) -> Vault:
    return Vault(db_path=db)


@click.group()
@click.version_option(__version__, prog_name="alias-vault")
@click.option("--db", default=None, envvar="ALIAS_VAULT_DB", help="Path to vault database.")
@click.pass_context
def cli(ctx: click.Context, db: str | None) -> None:
    """Alias Vault - Manage, search, and sync shell aliases.

    Store all your aliases in one place. Export to any shell format.
    Track usage. Never lose an alias again.
    """
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


@cli.command()
@click.argument("name")
@click.argument("command")
@click.option("--desc", "-d", default="", help="Description of the alias.")
@click.option("--tags", "-t", default="", help="Comma-separated tags.")
@click.option(
    "--shell", "-s", default="all",
    type=click.Choice(["all", "bash", "zsh", "fish"]),
    help="Target shell.",
)
@click.pass_context
def add(ctx: click.Context, name: str, command: str, desc: str, tags: str, shell: str) -> None:
    """Add a new alias to the vault."""
    vault = _get_vault(ctx.obj["db"])
    try:
        alias = vault.add(name, command, description=desc, tags=tags, shell=shell)
        console.print(f"[green]Added alias:[/] {alias['name']} = {alias['command']}")
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)
    finally:
        vault.close()


@cli.command(name="list")
@click.option("--shell", "-s", default=None, help="Filter by shell.")
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.option(
    "--sort", "sort_by", default="name",
    type=click.Choice(["name", "use_count", "created_at"]),
    help="Sort order.",
)
@click.option("--quiet", "-q", is_flag=True, help="Only print alias names.")
@click.pass_context
def list_cmd(ctx: click.Context, shell: str | None, tag: str | None, sort_by: str, quiet: bool) -> None:
    """List all aliases in the vault."""
    vault = _get_vault(ctx.obj["db"])
    aliases = vault.list_all(shell=shell, tag=tag, sort_by=sort_by)
    vault.close()

    if not aliases:
        console.print("[yellow]No aliases found.[/]")
        return

    if quiet:
        for a in aliases:
            click.echo(a["name"])
        return

    table = Table(title=f"Aliases ({len(aliases)})")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Command", style="white")
    table.add_column("Shell", style="magenta")
    table.add_column("Uses", style="green", justify="right")
    table.add_column("Tags", style="dim")

    for a in aliases:
        table.add_row(
            a["name"],
            a["command"][:60] + ("..." if len(a["command"]) > 60 else ""),
            a.get("shell", "all"),
            str(a.get("use_count", 0)),
            a.get("tags", ""),
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--shell", "-s", default=None, help="Filter by shell.")
@click.option("--tag", "-t", default=None, help="Filter by tag.")
@click.pass_context
def search(ctx: click.Context, query: str, shell: str | None, tag: str | None) -> None:
    """Search aliases by name, command, or description."""
    vault = _get_vault(ctx.obj["db"])
    aliases = vault.list_all()
    vault.close()

    results = search_aliases(aliases, query, shell=shell, tag=tag)

    if not results:
        console.print(f"[yellow]No aliases matching '{query}'.[/]")
        return

    table = Table(title=f"Search: '{query}' ({len(results)} results)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Command", style="white")
    table.add_column("Score", style="green", justify="right")
    table.add_column("Uses", style="dim", justify="right")

    for r in results:
        table.add_row(
            r["name"],
            r["command"][:60] + ("..." if len(r["command"]) > 60 else ""),
            f"{r['match_score']:.2f}",
            str(r.get("use_count", 0)),
        )

    console.print(table)


@cli.command()
@click.argument("name")
@click.pass_context
def remove(ctx: click.Context, name: str) -> None:
    """Remove an alias from the vault."""
    vault = _get_vault(ctx.obj["db"])
    if vault.remove(name):
        console.print(f"[green]Removed alias:[/] {name}")
    else:
        console.print(f"[red]Alias '{name}' not found.[/]")
        sys.exit(1)
    vault.close()


@cli.command(name="export")
@click.option(
    "--format", "-f", "fmt", default="bash",
    type=click.Choice(["bash", "zsh", "fish", "json", "yaml"]),
    help="Export format.",
)
@click.option("--output", "-o", default=None, help="Output file (default: stdout).")
@click.option("--shell", "-s", default=None, help="Filter by shell.")
@click.pass_context
def export_cmd(ctx: click.Context, fmt: str, output: str | None, shell: str | None) -> None:
    """Export aliases to a shell or data format."""
    vault = _get_vault(ctx.obj["db"])
    aliases = vault.list_all(shell=shell)
    vault.close()

    if not aliases:
        console.print("[yellow]No aliases to export.[/]")
        return

    content = export_aliases(aliases, fmt=fmt)

    if output:
        with open(output, "w") as f:
            f.write(content)
        console.print(f"[green]Exported {len(aliases)} aliases to {output}[/]")
    else:
        click.echo(content)


@cli.command(name="import")
@click.argument("files", nargs=-1)
@click.option("--auto", "-a", is_flag=True, help="Auto-discover and import from all shell configs.")
@click.pass_context
def import_cmd(ctx: click.Context, files: tuple[str, ...], auto: bool) -> None:
    """Import aliases from shell config files.

    Import from specific files or use --auto to discover and import
    from all shell configs in your home directory.
    """
    vault = _get_vault(ctx.obj["db"])

    all_aliases: list = []

    if auto:
        configs = discover_shell_configs()
        if not configs:
            console.print("[yellow]No shell config files found.[/]")
            vault.close()
            return
        console.print(f"[bold]Found {len(configs)} config files:[/]")
        for c in configs:
            console.print(f"  {c}")
        all_aliases = import_all_discovered()
    else:
        if not files:
            console.print("[red]Provide file paths or use --auto.[/]")
            vault.close()
            sys.exit(1)
        for filepath in files:
            try:
                aliases = import_from_file(filepath)
                all_aliases.extend(aliases)
                console.print(f"  [green]Parsed {len(aliases)} aliases from {filepath}[/]")
            except FileNotFoundError as e:
                console.print(f"  [red]{e}[/]")
            except Exception as e:
                console.print(f"  [red]Error parsing {filepath}: {e}[/]")

    if all_aliases:
        added = vault.bulk_add(all_aliases, skip_duplicates=True)
        console.print(f"\n[green]Imported {added} new aliases[/] (skipped {len(all_aliases) - added} duplicates)")
    else:
        console.print("[yellow]No aliases found to import.[/]")

    vault.close()


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show alias usage statistics."""
    vault = _get_vault(ctx.obj["db"])
    aliases = vault.list_all()
    vault.close()

    if not aliases:
        console.print("[yellow]No aliases in vault.[/]")
        return

    summary = get_stats_summary(aliases)

    console.print("\n[bold]Alias Vault Statistics[/]\n")
    console.print(f"  Total aliases:  {summary['total_aliases']}")
    console.print(f"  Total uses:     {summary['total_uses']}")
    console.print(f"  Used aliases:   {summary['used_aliases']}")
    console.print(f"  Never used:     {summary['never_used']}")
    console.print(f"  Usage rate:     {summary['usage_rate']}")
    console.print(f"  Avg uses:       {summary['avg_uses']}")

    if summary["by_shell"]:
        console.print("\n  [bold]By Shell:[/]")
        for shell, count in sorted(summary["by_shell"].items()):
            console.print(f"    {shell}: {count}")

    if summary["by_tag"]:
        console.print("\n  [bold]Top Tags:[/]")
        for tag, count in list(summary["by_tag"].items())[:10]:
            console.print(f"    {tag}: {count}")

    # Most used
    most_used = get_most_used(aliases, limit=5)
    if most_used:
        console.print("\n  [bold]Most Used:[/]")
        for a in most_used:
            console.print(f"    {a['name']} ({a['use_count']} uses): {a['command'][:50]}")

    # Never used
    never = get_never_used(aliases)
    if never and len(never) <= 10:
        console.print("\n  [bold]Never Used:[/]")
        for a in never:
            console.print(f"    {a['name']}: {a['command'][:50]}")

    console.print()


@cli.command()
@click.option(
    "--shell", "-s", default="bash",
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell to generate snippet for.",
)
def apply(shell: str) -> None:
    """Generate shell snippet to source aliases from vault.

    Add the output to your shell's rc file to auto-load aliases.
    """
    snippet = generate_source_snippet("", shell=shell)
    click.echo(snippet)


@cli.command(name="record-usage")
@click.argument("name")
@click.pass_context
def record_usage(ctx: click.Context, name: str) -> None:
    """Record that an alias was used (called by shell hook)."""
    vault = _get_vault(ctx.obj["db"])
    vault.record_usage(name)
    vault.close()


@cli.command()
@click.option(
    "--shell", "-s", default="bash",
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell to generate hook for.",
)
def hook(shell: str) -> None:
    """Generate a shell hook for tracking alias usage."""
    click.echo(generate_tracking_hook(shell))


if __name__ == "__main__":
    cli()
