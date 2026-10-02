# coding: utf-8

import pytest

from howl_editor.core.blob_cache import BlobCache


@pytest.fixture
def calls():
    return []


@pytest.fixture
def factory(calls):
    def build(blob: bytes) -> str:
        calls.append(blob)
        return f"parsed:{blob.decode()}"

    return build


class TestCaching:

    def test_same_content_is_built_once(self, factory, calls):
        cache = BlobCache()

        assert cache.get(b"song", factory) == "parsed:song"
        assert cache.get(b"song", factory) == "parsed:song"
        assert len(calls) == 1

    def test_an_edited_blob_misses(self, factory, calls):
        cache = BlobCache()

        cache.get(b"song", factory)
        cache.get(b"song-edited", factory)

        assert len(calls) == 2

    def test_equal_content_in_a_different_object_still_hits(self, factory, calls):
        # Identity would miss here; blobs are rebuilt constantly.
        cache = BlobCache()

        cache.get(b"song", factory)
        cache.get(bytes(bytearray(b"song")), factory)

        assert len(calls) == 1

    def test_clear_forgets_everything(self, factory, calls):
        cache = BlobCache()

        cache.get(b"song", factory)
        cache.clear()
        cache.get(b"song", factory)

        assert len(calls) == 2


class TestSalt:

    def test_a_different_salt_is_a_different_entry(self, factory, calls):
        cache = BlobCache()

        cache.get(b"bank", factory, salt=b"sizes-a")
        cache.get(b"bank", factory, salt=b"sizes-b")

        assert len(calls) == 2

    def test_the_same_salt_hits(self, factory, calls):
        cache = BlobCache()

        cache.get(b"bank", factory, salt=b"sizes-a")
        cache.get(b"bank", factory, salt=b"sizes-a")

        assert len(calls) == 1


class TestEviction:

    def test_oldest_entry_is_dropped_when_full(self, factory, calls):
        cache = BlobCache(max_entries=2)

        cache.get(b"a", factory)
        cache.get(b"b", factory)
        cache.get(b"c", factory)
        cache.get(b"a", factory)

        assert len(calls) == 4

    def test_a_reused_entry_outlives_an_idle_one(self, factory, calls):
        cache = BlobCache(max_entries=2)

        cache.get(b"a", factory)
        cache.get(b"b", factory)
        cache.get(b"a", factory)   # 'a' is now the most recently used
        cache.get(b"c", factory)   # evicts 'b'
        cache.get(b"a", factory)

        assert calls == [b"a", b"b", b"c"]
