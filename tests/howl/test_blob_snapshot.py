# coding: utf-8

from howl_editor.howl.blob_snapshot import BlobSnapshot
from howl_editor.models import HowlFile


class TestCapture:

    def test_starts_empty(self):
        snap = BlobSnapshot()

        assert snap.has_snapshot() is False
        assert snap.banks is None
        assert snap.songs is None

    def test_captures_banks_and_songs(self):
        snap = BlobSnapshot()
        hwl = HowlFile(banks=[b"a", b"b"], songs=[b"x"])

        snap.capture(hwl)

        assert snap.has_snapshot() is True
        assert snap.banks == [b"a", b"b"]
        assert snap.songs == [b"x"]

    def test_capture_decouples_from_live_lists(self):
        snap = BlobSnapshot()
        hwl = HowlFile(banks=[b"a"], songs=[b"x"])

        snap.capture(hwl)
        hwl.banks.append(b"new")  # mutate after capture

        assert snap.banks == [b"a"]  # snapshot must be unaffected

    def test_recapture_overwrites(self):
        snap = BlobSnapshot()
        snap.capture(HowlFile(banks=[b"a"]))
        snap.capture(HowlFile(banks=[b"b"]))

        assert snap.banks == [b"b"]


class TestClear:

    def test_clear_resets(self):
        snap = BlobSnapshot()
        snap.capture(HowlFile(banks=[b"a"], songs=[b"x"]))

        snap.clear()

        assert snap.has_snapshot() is False
        assert snap.banks is None
        assert snap.songs is None


class TestOriginalLookup:

    def test_returns_blob_by_index(self):
        snap = BlobSnapshot()
        snap.capture(HowlFile(banks=[b"a", b"b"], songs=[b"x", b"y"]))

        assert snap.original_bank(0) == b"a"
        assert snap.original_bank(1) == b"b"
        assert snap.original_song(0) == b"x"

    def test_returns_none_when_no_snapshot(self):
        snap = BlobSnapshot()

        assert snap.original_bank(0) is None
        assert snap.original_song(0) is None

    def test_returns_none_for_out_of_range(self):
        snap = BlobSnapshot()
        snap.capture(HowlFile(banks=[b"a"]))

        assert snap.original_bank(5) is None
        assert snap.original_bank(-1) is None
