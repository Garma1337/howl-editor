# coding: utf-8

"""
Minimal template engine supporting variable substitution, for-loops, conditionals,
and file includes.

Syntax:
    {{ variable }}              — HTML-escaped variable substitution
    {{ variable | raw }}        — unescaped substitution (for pre-built HTML fragments)
    {% for item in items %}     — loop over a list; 'item' becomes the loop variable
        {{ item.field }}        — dot access on loop variable
    {% endfor %}
    {% if variable %}           — conditional block (truthy check)
    {% endif %}
    {% include "filename" %}    — inline another template file (no variable expansion)
"""

import re
from html import escape
from pathlib import Path


_VAR_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
_BLOCK_RE = re.compile(
    r"\{%\s*(for\s+\w+\s+in\s+[\w.]+|endfor|if\s+[\w.]+|endif|include\s+\".+?\")\s*%\}"
)
_TOKEN_RE = re.compile(
    r"(\{\{.+?\}\}|\{%.+?%\})", re.DOTALL
)


class TemplateEngine:
    """Loads and renders HTML templates with variable substitution, loops, and conditionals."""

    def __init__(self, template_dir: str | Path):
        self._dir = Path(template_dir)
        self._cache: dict[str, str] = {}

    def render(self, template_name: str, **context) -> str:
        """Render a template file with the given context variables."""
        source = self._load(template_name)
        return self._evaluate(source, context)

    def render_string(self, source: str, **context) -> str:
        """Render a template string directly."""
        return self._evaluate(source, context)

    def _load(self, name: str) -> str:
        if name not in self._cache:
            path = self._dir / name
            self._cache[name] = path.read_text(encoding="utf-8")

        return self._cache[name]

    def _evaluate(self, source: str, context: dict) -> str:
        tokens = _TOKEN_RE.split(source)
        return self._render_tokens(tokens, 0, context)[0]

    def _render_tokens(
        self, tokens: list[str], pos: int, context: dict,
    ) -> tuple[str, int]:
        parts: list[str] = []

        while pos < len(tokens):
            token = tokens[pos]

            if token.startswith("{%"):
                directive = token.strip("{%} ")

                if directive.startswith("for "):
                    result, pos = self._handle_for(tokens, pos, directive, context)
                    parts.append(result)
                    continue

                elif directive.startswith("if "):
                    result, pos = self._handle_if(tokens, pos, directive, context)
                    parts.append(result)
                    continue

                elif directive.startswith("include "):
                    filename = directive.split('"')[1]
                    parts.append(self._load(filename))
                    pos += 1
                    continue

                elif directive in ("endfor", "endif"):
                    return "".join(parts), pos + 1

            elif token.startswith("{{"):
                parts.append(self._resolve_var(token, context))

            else:
                parts.append(token)

            pos += 1

        return "".join(parts), pos

    def _handle_for(
        self, tokens: list[str], pos: int, directive: str, context: dict,
    ) -> tuple[str, int]:
        # Parse "for item in items" or "for item in parent.items"
        match = re.match(r"for\s+(\w+)\s+in\s+([\w.]+)", directive)
        if not match:
            return "", pos + 1

        loop_var = match.group(1)
        list_expr = match.group(2)
        items = self._lookup(list_expr, context) or []

        # Find the body tokens between for and endfor
        body_start = pos + 1
        parts: list[str] = []

        for item in items:
            child_ctx = {**context, loop_var: item}
            result, end_pos = self._render_tokens(tokens, body_start, child_ctx)
            parts.append(result)

        # Skip past endfor (need to find it even if items was empty)
        if not items:
            _, end_pos = self._render_tokens(tokens, body_start, context)

        return "".join(parts), end_pos

    def _handle_if(
        self, tokens: list[str], pos: int, directive: str, context: dict,
    ) -> tuple[str, int]:
        var_name = directive[3:].strip()
        value = self._lookup(var_name, context)

        body_start = pos + 1
        result, end_pos = self._render_tokens(tokens, body_start, context)

        if value:
            return result, end_pos

        return "", end_pos

    def _resolve_var(self, token: str, context: dict) -> str:
        inner = token.strip("{} ")

        raw = False
        if inner.endswith("| raw"):
            inner = inner[:-5].strip()
            raw = True

        value = self._lookup(inner, context)
        text = str(value) if value is not None else ""

        if raw:
            return text

        return escape(text)

    def _lookup(self, expr: str, context: dict):
        """Resolve a dotted expression like 'item.name' against the context."""
        parts = expr.split(".")
        value = context.get(parts[0])

        for part in parts[1:]:
            if value is None:
                return None
            
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)

        return value
