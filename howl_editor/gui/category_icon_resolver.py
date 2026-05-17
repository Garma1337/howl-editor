# coding: utf-8

import re
from pathlib import Path


class CategoryIconResolver:
    """Maps a category name to a custom image file on disk.

    Looks up `{slug}.{ext}` in the configured image directory. The slug is the
    category name lowercased, with `&` becoming `and` and any other run of
    non-alphanumeric characters collapsed to a single underscore.

    Examples:
      "Race Tracks"           -> race_tracks
      "Menus & Cinematics"    -> menus_and_cinematics
      "SFX (universal)"       -> sfx_universal
      "Sound Effects (OtherFX)" -> sound_effects_otherfx
    """

    _EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp")
    _NON_ALNUM = re.compile(r"[^a-z0-9]+")

    def __init__(self, image_dir: str | Path):
        self._dir = Path(image_dir)

    @property
    def image_dir(self) -> Path:
        return self._dir

    def resolve(self, name: str, sub_dir: str | None = None) -> Path | None:
        """Find an image file matching `name` either in the root images dir
        (category cards) or in a sub-directory (per-entry icons)."""
        slug = self.slugify(name)

        if not slug:
            return None

        base = self._dir / self.slugify(sub_dir) if sub_dir else self._dir

        for ext in self._EXTENSIONS:
            candidate = base / f"{slug}{ext}"
            if candidate.is_file():
                return candidate

        return None

    def resolve_entry(self, entry_name: str, category_name: str) -> Path | None:
        """Find a per-entry icon (e.g. character portrait, boss avatar).

        Lookup path: `<images>/<category_slug>/<entry_slug>.<ext>`.
        """
        return self.resolve(entry_name, sub_dir=category_name)

    def resolve_leaf(self, leaf_name: str) -> Path | None:
        """Find a per-leaf icon — used for shared leaf names like the Aku Aku
        and Uka Uka mask sequences which appear under every song 0-27.

        Lookup path: `<images>/leaves/<leaf_slug>.<ext>`.
        """
        return self.resolve(leaf_name, sub_dir="leaves")

    @classmethod
    def slugify(cls, name: str) -> str:
        lowered = name.lower().replace("&", "and")
        slug = cls._NON_ALNUM.sub("_", lowered).strip("_")
        return slug
