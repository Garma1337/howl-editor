# Card images

Three levels of custom images are supported on the Main tab:

1. **Category card icons** — shown on the big cards on the grid (Race Tracks, Characters, Boss Themes, etc.). Files live in this root directory.
2. **Per-entry icons** — shown on each entry row inside a category's detail view (e.g. a portrait for Crash, an avatar for Papu Papu). Files live in a sub-directory named after the category slug.
3. **Per-leaf icons** — shown on each playable sequence/sample row. Useful for the shared mask sequences (Aku Aku, Uka Uka) that appear under every song 0–27. Files live in the `leaves/` sub-directory.

If no image is found at any level, the UI falls back to the built-in emoji icon for that level.

## Filename rules

A name is lowercased; `&` becomes `and`; any other run of non-alphanumeric characters (spaces, parentheses, punctuation, `:`) becomes a single underscore; leading and trailing underscores are stripped.

| Source name              | Slug                      |
|--------------------------|---------------------------|
| Race Tracks              | `race_tracks`             |
| Menus & Cinematics       | `menus_and_cinematics`    |
| SFX (universal)          | `sfx_universal`           |
| Sound Effects (OtherFX)  | `sound_effects_otherfx`   |
| Boss: Papu Papu          | `boss_papu_papu`          |
| Sewer Speedway           | `sewer_speedway`          |
| Crash Bandicoot          | `crash_bandicoot`         |
| Main music               | `main_music`              |
| Aku Aku mask             | `aku_aku_mask`            |
| Uka Uka mask             | `uka_uka_mask`            |

## Layout

```
images/
├── race_tracks.png                       ← category card
├── battle_arenas.png
├── adventure_hub.png
├── boss_themes.png
├── menus_and_cinematics.png
├── characters.png
├── sfx_universal.png
├── sound_effects_otherfx.png
├── engine_sounds_enginefx.png
├── custom.png
│
├── race_tracks/                          ← per-entry icons for that category
│   ├── dingo_canyon.png
│   ├── sewer_speedway.png
│   └── ...
├── characters/
│   ├── crash_bandicoot.png
│   ├── dr_neo_cortex.png
│   └── ...
├── boss_themes/
│   ├── boss_ripper_roo.png
│   ├── boss_papu_papu.png
│   └── ...
│
└── leaves/                               ← per-leaf icons (shared across categories)
    ├── main_music.png
    ├── aku_aku_mask.png
    └── uka_uka_mask.png
```

- A per-entry image is looked up at `<category_slug>/<entry_slug>.<ext>`. If the file doesn't exist the entry row falls back to the category emoji.
- A per-leaf image is looked up at `leaves/<leaf_slug>.<ext>`. If the file doesn't exist the row falls back to the leaf's emoji (🎵 / 🪄 / 👹 / 🔊). These match by the human-readable leaf name (Main music, Aku Aku mask, Uka Uka mask) regardless of which song the leaf belongs to.

Sub-directories are only created when you start adding icons — empty ones aren't required.

## Accepted formats

`.png`, `.jpg`, `.jpeg`, `.svg`, `.webp` — first match wins in that order.

## Recommended sizes

- **Category cards**: 80×80 px (scaled into a 64 px box)
- **Entry rows**: 32×32 px (scaled into a 32 px box)
- **Leaf rows**: 22×22 px (scaled into a 22 px box)

Transparent backgrounds (PNG / SVG) look best on both light and dark themes.
