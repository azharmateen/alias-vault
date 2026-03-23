"""Vault storage: SQLite-backed alias database with CRUD operations."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "alias-vault",
    "vault.db",
)


class Vault:
    """SQLite-backed alias vault."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                command TEXT NOT NULL,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                shell TEXT DEFAULT 'all',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                use_count INTEGER DEFAULT 0,
                last_used_at TEXT DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_aliases_name ON aliases(name);
            CREATE INDEX IF NOT EXISTS idx_aliases_tags ON aliases(tags);
        """)
        self.conn.commit()

    def add(
        self,
        name: str,
        command: str,
        description: str = "",
        tags: str = "",
        shell: str = "all",
    ) -> dict[str, Any]:
        """Add a new alias to the vault."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                """INSERT INTO aliases (name, command, description, tags, shell, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, command, description, tags, shell, now, now),
            )
            self.conn.commit()
            return self.get(name)  # type: ignore
        except sqlite3.IntegrityError:
            raise ValueError(f"Alias '{name}' already exists. Use 'alias-vault update' to modify.")

    def get(self, name: str) -> dict[str, Any] | None:
        """Get an alias by name."""
        row = self.conn.execute(
            "SELECT * FROM aliases WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def update(
        self,
        name: str,
        command: str | None = None,
        description: str | None = None,
        tags: str | None = None,
        shell: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing alias."""
        existing = self.get(name)
        if not existing:
            raise ValueError(f"Alias '{name}' not found.")

        updates = {}
        if command is not None:
            updates["command"] = command
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tags
        if shell is not None:
            updates["shell"] = shell

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [name]
            self.conn.execute(
                f"UPDATE aliases SET {set_clause} WHERE name = ?",
                values,
            )
            self.conn.commit()

        return self.get(name)  # type: ignore

    def remove(self, name: str) -> bool:
        """Remove an alias by name."""
        cursor = self.conn.execute("DELETE FROM aliases WHERE name = ?", (name,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_all(
        self,
        shell: str | None = None,
        tag: str | None = None,
        sort_by: str = "name",
    ) -> list[dict[str, Any]]:
        """List all aliases with optional filtering."""
        query = "SELECT * FROM aliases WHERE 1=1"
        params: list[Any] = []

        if shell:
            query += " AND (shell = ? OR shell = 'all')"
            params.append(shell)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        valid_sorts = {"name", "use_count", "created_at", "updated_at", "last_used_at"}
        if sort_by in valid_sorts:
            direction = "DESC" if sort_by in ("use_count", "created_at", "updated_at", "last_used_at") else "ASC"
            query += f" ORDER BY {sort_by} {direction}"
        else:
            query += " ORDER BY name ASC"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def record_usage(self, name: str) -> None:
        """Record that an alias was used."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE aliases SET use_count = use_count + 1, last_used_at = ? WHERE name = ?",
            (now, name),
        )
        self.conn.commit()

    def count(self) -> int:
        """Return total number of aliases."""
        row = self.conn.execute("SELECT COUNT(*) FROM aliases").fetchone()
        return row[0]

    def bulk_add(self, aliases: list[dict[str, Any]], skip_duplicates: bool = True) -> int:
        """Add multiple aliases at once. Returns count of added aliases."""
        added = 0
        now = datetime.now(timezone.utc).isoformat()
        for alias in aliases:
            try:
                self.conn.execute(
                    """INSERT INTO aliases (name, command, description, tags, shell, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        alias["name"],
                        alias["command"],
                        alias.get("description", ""),
                        alias.get("tags", ""),
                        alias.get("shell", "all"),
                        now,
                        now,
                    ),
                )
                added += 1
            except sqlite3.IntegrityError:
                if not skip_duplicates:
                    raise
        self.conn.commit()
        return added

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
