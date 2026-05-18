# coding: utf-8

import hashlib
from collections import OrderedDict
from pathlib import Path

from howl_editor.file_format_registry import FileFormatRegistry


class AudioCache:
    """Two-tier cache for rendered audio WAVs."""

    _NONE_SENTINEL = b"\x00\xff\xff\xff"

    def __init__(self, cache_dir: str | Path, memory_limit: int = 8):
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._memory: "OrderedDict[str, bytes]" = OrderedDict()
        self._memory_limit = memory_limit

    def get(self, key: str) -> bytes | None:
        """Return cached WAV bytes or None. Promotes the entry to MRU when
        served from memory and lazily fills the memory tier from disk."""
        cached = self._memory.get(key)
        if cached is not None:
            self._memory.move_to_end(key)
            return cached

        path = self._path_for(key)
        if not path.is_file():
            return None

        try:
            data = path.read_bytes()
        except OSError:
            return None

        self._remember(key, data)
        return data

    def put(self, key: str, wav: bytes) -> None:
        """Store WAV bytes under `key`. Memory writes are guaranteed; the
        disk write is opportunistic — if it fails the in-memory copy still
        wins for the rest of the session."""
        self._remember(key, wav)

        try:
            self._path_for(key).write_bytes(wav)
        except OSError:
            pass

    def make_key(self, *parts) -> str:
        """Build a stable SHA-1 hex digest from `bytes`, `int`, tuples/lists
        of bytes/ints, and `None`. Length-prefixing keeps `b"AB" + b"CD"`
        from colliding with `b"ABCD"` etc."""
        digest = hashlib.sha1()

        for part in parts:
            self._update(digest, part)

        return digest.hexdigest()

    def clear_memory(self) -> None:
        self._memory.clear()

    def clear_disk(self) -> int:
        count = 0

        for f in self._dir.glob(f"*{FileFormatRegistry.WAV.extension}"):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass

        return count

    def clear(self) -> int:
        self.clear_memory()
        return self.clear_disk()

    @property
    def cache_dir(self) -> Path:
        return self._dir

    @property
    def memory_size(self) -> int:
        return len(self._memory)

    def _update(self, digest, part) -> None:
        if part is None:
            digest.update(self._NONE_SENTINEL)
        elif isinstance(part, bytes):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
        elif isinstance(part, bool):
            digest.update(b"\x01" if part else b"\x00")
        elif isinstance(part, int):
            digest.update(b"i")
            digest.update(part.to_bytes(8, "big", signed=True))
        elif isinstance(part, (tuple, list)):
            digest.update(b"(")
            digest.update(len(part).to_bytes(8, "big"))
            for item in part:
                self._update(digest, item)
        else:
            raise TypeError(
                f"AudioCache.make_key: unsupported type {type(part).__name__}",
            )

    def _remember(self, key: str, data: bytes) -> None:
        self._memory[key] = data
        self._memory.move_to_end(key)

        while len(self._memory) > self._memory_limit:
            self._memory.popitem(last=False)

    def _path_for(self, key: str) -> Path:
        return self._dir / f"{key}{FileFormatRegistry.WAV.extension}"
