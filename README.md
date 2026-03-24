# Alias Vault

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


**Your aliases are scattered across `.bashrc`, `.zshrc`, `.config/fish/config.fish`, and a dozen other files.** Alias Vault puts them all in one searchable, exportable database.

```
$ alias-vault import --auto
Found 3 config files:
  /home/user/.bashrc
  /home/user/.zshrc
  /home/user/.config/fish/config.fish
Imported 47 new aliases (skipped 12 duplicates)

$ alias-vault search docker
┌──────────┬─────────────────────────────┬───────┬──────┐
│ Name     │ Command                     │ Score │ Uses │
├──────────┼─────────────────────────────┼───────┼──────┤
│ dps      │ docker ps --format "table"  │ 0.90  │ 142  │
│ dex      │ docker exec -it             │ 0.85  │ 89   │
│ dcu      │ docker compose up -d        │ 0.80  │ 67   │
│ dcl      │ docker compose logs -f      │ 0.75  │ 31   │
└──────────┴─────────────────────────────┴───────┴──────┘

$ alias-vault export --format zsh > ~/.zsh_aliases
Exported 47 aliases to ~/.zsh_aliases
```

## Why Alias Vault?

- **One database** for all shells - bash, zsh, fish
- **Fuzzy search** across names, commands, descriptions, and tags
- **Import** from any existing shell config with duplicate detection
- **Export** to bash, zsh, fish, JSON, or YAML
- **Usage tracking** with shell hooks - know which aliases you actually use
- **SQLite storage** - fast, portable, no server needed

## Install

```bash
pip install alias-vault
```

## Quick Start

```bash
# Add aliases manually
alias-vault add gs "git status" --desc "Git status" --tags git
alias-vault add gp "git push" --desc "Git push" --tags git
alias-vault add ll "ls -la" --tags filesystem

# Or import from your existing config
alias-vault import ~/.bashrc ~/.zshrc
alias-vault import --auto  # auto-discover all configs

# Search
alias-vault search git

# Export to your shell
alias-vault export --format zsh >> ~/.zshrc
alias-vault export --format fish > ~/.config/fish/aliases.fish

# View stats
alias-vault stats
```

## Commands

| Command | Description |
|---------|-------------|
| `alias-vault add <name> <command>` | Add a new alias |
| `alias-vault list [--shell bash] [--tag git]` | List all aliases |
| `alias-vault search <query>` | Fuzzy search aliases |
| `alias-vault remove <name>` | Remove an alias |
| `alias-vault export [--format bash\|zsh\|fish\|json\|yaml]` | Export aliases |
| `alias-vault import <files...> [--auto]` | Import from shell configs |
| `alias-vault stats` | Usage analytics |
| `alias-vault apply [--shell bash]` | Generate shell source snippet |
| `alias-vault hook [--shell bash]` | Generate usage tracking hook |

## Usage Tracking

Add the tracking hook to your shell config to automatically track which aliases you use:

```bash
# Generate the hook
alias-vault hook --shell zsh >> ~/.zshrc

# Then check your stats
alias-vault stats
```

## License

MIT
