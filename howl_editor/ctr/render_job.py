# coding: utf-8

"""The song render as a standalone job, run through ProcessTaskRunner.

A child interpreter re-imports rather than inheriting, so everything here has
to be importable on its own and take plain data: the job builds its own
renderer from the same collaborators the container wires up.
"""

from howl_editor.audio.wav_writer import WavWriter
from howl_editor.core.progress import ProgressReporter
from howl_editor.ctr.cseq_renderer import CseqRenderer
from howl_editor.ctr.formats.cseq.models import CseqFile
from howl_editor.ctr.voice.gain_calculator import GainCalculator
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1.adsr_decoder import AdsrDecoder
from howl_editor.ps1.formats.vag.decoder import VagDecoder


def build_renderer() -> CseqRenderer:
    wav_writer = WavWriter()

    return CseqRenderer(
        VagDecoder(wav_writer), AdsrDecoder(), wav_writer,
        PitchCalculator(), GainCalculator(),
    )


def render_song_wav(
    cseq: CseqFile,
    song_index: int,
    sample_data: dict[int, bytes],
    output_rate: int = 22050,
    active_tracks: list[int] | None = None,
    progress: ProgressReporter | None = None,
) -> bytes:
    """Render one sub-song to WAV bytes."""
    return build_renderer().render_song_to_wav(
        cseq, song_index, sample_data, output_rate, active_tracks, progress,
    )
