# coding: utf-8

import tempfile
from pathlib import Path


APP_CACHE_ROOT = Path(tempfile.gettempdir()) / "howl-editor"
DECODED_WAV_CACHE_DIR = APP_CACHE_ROOT
RENDERED_SONG_CACHE_DIR = APP_CACHE_ROOT / "renders"
