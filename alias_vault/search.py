"""Search functionality with fuzzy matching."""

from __future__ import annotations

from typing import Any


def fuzzy_match(query: str, text: str) -> float:
    """Simple fuzzy match score between 0.0 and 1.0.

    Uses character-level subsequence matching with position penalty.
    """
    query = query.lower()
    text = text.lower()

    if query == text:
        return 1.0
    if query in text:
        return 0.9 - (len(text) - len(query)) * 0.01

    # Subsequence matching
    query_idx = 0
    matched = 0
    last_match_pos = -2  # Track consecutive matches
    consecutive_bonus = 0.0

    for text_idx, char in enumerate(text):
        if query_idx < len(query) and char == query[query_idx]:
            matched += 1
            if text_idx == last_match_pos + 1:
                consecutive_bonus += 0.1
            last_match_pos = text_idx
            query_idx += 1

    if matched < len(query):
        return 0.0

    base_score = matched / max(len(query), len(text))
    return min(base_score + consecutive_bonus, 0.89)


def search_aliases(
    aliases: list[dict[str, Any]],
    query: str,
    fields: list[str] | None = None,
    min_score: float = 0.3,
    shell: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """Search aliases with fuzzy matching across multiple fields.

    Args:
        aliases: List of alias dicts.
        query: Search query string.
        fields: Fields to search in. Default: name, command, description, tags.
        min_score: Minimum match score to include (0.0 to 1.0).
        shell: Optional shell filter.
        tag: Optional tag filter.

    Returns:
        Sorted list of matching aliases with 'match_score' added.
    """
    if fields is None:
        fields = ["name", "command", "description", "tags"]

    results = []

    for alias in aliases:
        # Apply filters
        if shell and alias.get("shell", "all") not in (shell, "all"):
            continue
        if tag and tag.lower() not in alias.get("tags", "").lower():
            continue

        # Calculate best match score across fields
        best_score = 0.0
        field_weights = {
            "name": 1.5,
            "command": 1.0,
            "description": 0.8,
            "tags": 0.7,
        }

        for field in fields:
            value = str(alias.get(field, ""))
            if not value:
                continue
            score = fuzzy_match(query, value)
            weight = field_weights.get(field, 1.0)
            weighted_score = score * weight
            best_score = max(best_score, weighted_score)

        if best_score >= min_score:
            result = dict(alias)
            result["match_score"] = round(best_score, 3)
            results.append(result)

    # Sort by score descending, then by use_count descending
    results.sort(key=lambda x: (-x["match_score"], -x.get("use_count", 0)))
    return results
