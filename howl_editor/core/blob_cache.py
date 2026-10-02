# coding: utf-8

from collections import OrderedDict
from collections.abc import Callable
from hashlib import blake2b
from typing import Any

DEFAULT_MAX_ENTRIES = 256
_KEY_BYTES = 16


class BlobCache:
    """Memoizes a derived value per blob, keyed by the blob's content.

    Editing a bank or song replaces its blob wholesale, so content is the
    natural key: an untouched blob keeps hitting the cache across rebuilds
    while an edited one misses exactly once. Identity would be unsafe — a
    freed blob's address can be reused by the next one."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES):
        self._max_entries = max_entries
        self._entries: OrderedDict[bytes, Any] = OrderedDict()

    def get(self, blob: bytes, factory: Callable[[bytes], Any], salt: bytes = b"") -> Any:
        """`salt` joins the key for a value that also depends on something
        outside the blob — a bank's slices, for instance, depend on the SPU
        size table as much as on the bank's own bytes."""
        key = blake2b(blob + salt, digest_size=_KEY_BYTES).digest()

        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]

        value = factory(blob)
        self._entries[key] = value
        self._trim()

        return value

    def clear(self) -> None:
        self._entries.clear()

    def _trim(self) -> None:
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
