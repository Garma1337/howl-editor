# coding: utf-8

from pathlib import Path


class StylesheetLoader:
    """Reads `.qss` files from a directory and caches them.

    Lets widget code stay free of inline stylesheet strings — each widget asks
    the loader for its named QSS file the same way HTML detail formatters ask
    `TemplateEngine` for their HTML templates.
    """

    def __init__(self, qss_dir: str | Path):
        self._dir = Path(qss_dir)
        self._cache: dict[str, str] = {}

    def load(self, name: str) -> str:
        if name not in self._cache:
            self._cache[name] = (self._dir / name).read_text(encoding="utf-8")

        return self._cache[name]
