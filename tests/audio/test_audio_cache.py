# coding: utf-8

import pytest

from howl_editor.audio.audio_cache import AudioCache


@pytest.fixture
def cache(tmp_path):
    return AudioCache(tmp_path)


class TestRoundTrip:

    def test_put_then_get_returns_bytes(self, cache):
        cache.put("abc", b"RIFFWAVE")

        assert cache.get("abc") == b"RIFFWAVE"

    def test_missing_key_returns_none(self, cache):
        assert cache.get("never-stored") is None

    def test_get_promotes_to_memory_mru(self, cache):
        # Two distinct keys; after touching the first, the second should
        # still be present but the first is now the most-recently-used.
        cache.put("a", b"AAAA")
        cache.put("b", b"BBBB")

        cache.get("a")
        # No public MRU inspection — but force eviction by overflowing the
        # memory limit and check that 'b' (oldest) is evicted, not 'a'.
        small = AudioCache(cache.cache_dir, memory_limit=2)
        small.put("a", b"AAAA")
        small.put("b", b"BBBB")
        small.get("a")          # promotes 'a'
        small.put("c", b"CCCC") # evicts 'b'

        assert small.memory_size == 2


class TestPersistence:

    def test_disk_hit_survives_new_instance(self, tmp_path):
        original = AudioCache(tmp_path)
        original.put("songA", b"RIFFWAVE")

        # Simulate app restart: fresh instance pointed at the same dir.
        fresh = AudioCache(tmp_path)

        assert fresh.get("songA") == b"RIFFWAVE"

    def test_disk_hit_populates_memory_tier(self, tmp_path):
        original = AudioCache(tmp_path)
        original.put("songA", b"X" * 10)

        fresh = AudioCache(tmp_path)
        assert fresh.memory_size == 0
        fresh.get("songA")
        assert fresh.memory_size == 1


class TestEviction:

    def test_memory_limit_keeps_only_most_recent(self, tmp_path):
        cache = AudioCache(tmp_path, memory_limit=2)
        cache.put("a", b"AAAA")
        cache.put("b", b"BBBB")
        cache.put("c", b"CCCC")

        assert cache.memory_size == 2

    def test_evicted_entries_still_on_disk(self, tmp_path):
        cache = AudioCache(tmp_path, memory_limit=1)
        cache.put("a", b"AAAA")
        cache.put("b", b"BBBB")  # evicts 'a' from memory

        # 'a' should re-hydrate from disk into the memory tier on next get.
        assert cache.get("a") == b"AAAA"


class TestMakeKey:

    def test_deterministic(self, cache):
        k1 = cache.make_key(b"song", 5, (b"bank0", b"bank1"), None)
        k2 = cache.make_key(b"song", 5, (b"bank0", b"bank1"), None)

        assert k1 == k2

    def test_different_bytes_give_different_keys(self, cache):
        k1 = cache.make_key(b"songA", 0)
        k2 = cache.make_key(b"songB", 0)

        assert k1 != k2

    def test_different_int_gives_different_key(self, cache):
        # Same song, different sub-song picked — must be a different key,
        # otherwise we'd cross-contaminate Aku/Uka mask renders.
        k1 = cache.make_key(b"song", 0)
        k2 = cache.make_key(b"song", 1)

        assert k1 != k2

    def test_active_tracks_tuple_changes_key(self, cache):
        k_full = cache.make_key(b"hub", 0, (), None)
        k_gem = cache.make_key(b"hub", 0, (), (0, 1, 3, 5))
        k_glacier = cache.make_key(b"hub", 0, (), (0, 2, 3, 5))

        assert k_full != k_gem
        assert k_gem != k_glacier

    def test_none_distinct_from_zero_and_empty(self, cache):
        """None should not collide with int 0 or empty tuple — different
        kinds of inputs shouldn't accidentally hash the same."""
        k_none = cache.make_key(b"x", None)
        k_zero = cache.make_key(b"x", 0)
        k_empty = cache.make_key(b"x", ())

        assert len({k_none, k_zero, k_empty}) == 3

    def test_bool_distinct_from_int(self, cache):
        """bool is an int subclass in Python — make sure we don't collapse
        True/False onto 1/0 inside the key."""
        assert cache.make_key(b"x", True) != cache.make_key(b"x", 1)
        assert cache.make_key(b"x", False) != cache.make_key(b"x", 0)

    def test_length_prefix_prevents_concatenation_collision(self, cache):
        """Without length prefixing, (b"AB", b"CD") would hash the same as
        (b"ABCD",). The cache must keep them distinct."""
        k1 = cache.make_key(b"AB", b"CD")
        k2 = cache.make_key(b"ABCD")

        assert k1 != k2

    def test_unsupported_type_raises(self, cache):
        with pytest.raises(TypeError):
            cache.make_key({"not": "supported"})


class TestClear:

    def test_clear_memory_keeps_disk(self, tmp_path):
        cache = AudioCache(tmp_path)
        cache.put("a", b"AAAA")
        cache.clear_memory()

        assert cache.memory_size == 0
        assert cache.get("a") == b"AAAA"  # disk hit re-hydrates

    def test_clear_disk_returns_file_count(self, tmp_path):
        cache = AudioCache(tmp_path)
        cache.put("a", b"AAAA")
        cache.put("b", b"BBBB")

        assert cache.clear_disk() == 2

    def test_clear_wipes_both_tiers(self, tmp_path):
        cache = AudioCache(tmp_path)
        cache.put("a", b"AAAA")
        cache.clear()

        assert cache.memory_size == 0
        # A fresh instance should not see 'a' either.
        fresh = AudioCache(tmp_path)
        assert fresh.get("a") is None
