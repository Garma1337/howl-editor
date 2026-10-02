# coding: utf-8

import os
import time
from struct import pack

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.gui.widget.waveform_widget import WaveformWidget


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qt_app):
    return WaveformWidget()


def _wav(samples: list[int], channels: int = 2) -> bytes:
    pcm = pack(f"<{len(samples)}h", *samples)
    header = (
        b"RIFF" + pack("<I", 36 + len(pcm)) + b"WAVEfmt " + pack("<I", 16)
        + pack("<HH", 1, channels) + pack("<II", 22050, 22050 * 2 * channels)
        + pack("<HH", 2 * channels, 16) + b"data" + pack("<I", len(pcm))
    )
    return header + pcm


class TestParsing:

    def test_every_sample_is_kept(self, widget):
        widget.set_wav(_wav([100, -100, 2000, -2000]))

        assert list(widget._samples) == [100, -100, 2000, -2000]

    def test_mono_is_read_the_same_way(self, widget):
        widget.set_wav(_wav([5, -5, 10], channels=1))

        assert list(widget._samples) == [5, -5, 10]

    def test_an_odd_trailing_byte_is_ignored(self, widget):
        widget.set_wav(_wav([7, -7]) + b"\x00")

        assert list(widget._samples) == [7, -7]

    def test_too_short_to_be_a_wav_clears_the_view(self, widget):
        widget.set_wav(_wav([1, 2]))

        widget.set_wav(b"short")

        assert list(widget._samples) == []

    def test_clear_empties_it(self, widget):
        widget.set_wav(_wav([1, 2]))

        widget.clear()

        assert list(widget._samples) == []


class TestCost:

    def test_a_song_sized_render_parses_quickly(self, widget):
        # ~2M frames, the size of a full song render.
        wav = _wav([(i % 2000) - 1000 for i in range(2_000_000)])

        start = time.perf_counter()
        widget.set_wav(wav)
        elapsed = time.perf_counter() - start

        assert len(widget._samples) == 2_000_000
        # The C-level parse lands near 2 ms; the old per-sample loop took 400.
        assert elapsed < 0.1
