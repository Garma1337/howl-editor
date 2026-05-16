# coding: utf-8

from pathlib import Path

from howl_editor.analysis.sample_classifier import SampleClassifier
from howl_editor.analysis.validator import BankCseqValidator
from howl_editor.audio.audio_player import AudioPlayer
from howl_editor.audio.cseq_renderer import CseqRenderer
from howl_editor.audio.decoder.adsr_decoder import AdsrDecoder
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.voice import PitchCalculator, GainCalculator
from howl_editor.audio.sample_lookup import SampleLookup
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.bank.builder import BankBuilder
from howl_editor.bank.reader import BankReader
from howl_editor.core import Container
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.editor import CseqEditor
from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.export.batch_exporter import BatchExporter
from howl_editor.gui.detail.bank_detail_formatter import BankDetailFormatter
from howl_editor.gui.detail.detail_formatter import DetailFormatter
from howl_editor.gui.detail.fx_detail_formatter import FxDetailFormatter
from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.gui.detail.song_detail_formatter import SongDetailFormatter
from howl_editor.howl.editor import HowlEditor
from howl_editor.howl.reader import HowlReader
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.howl.writer import HowlWriter
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.exporter import CseqMidiExporter
from howl_editor.sca.chunk_reader import ScaChunkReader
from howl_editor.sca.chunk_writer import ScaChunkWriter
from howl_editor.sca.metadata_codec import ScaMetadataCodec
from howl_editor.sca.reader import ScaReader
from howl_editor.sca.sample_sizes_extractor import SampleSizesExtractor
from howl_editor.sca.writer import ScaWriter
from howl_editor.vag.reader import VagReader
from howl_editor.vag.writer import VagWriter

_TEMPLATE_DIR = Path(__file__).parent / "gui" / "templates"

container = Container()
container.register("vlq_codec", lambda c: VlqCodec())
container.register("howl_reader", lambda c: HowlReader())
container.register("howl_writer", lambda c: HowlWriter())
container.register("howl_editor", lambda c: HowlEditor())
container.register("cseq_reader", lambda c: CseqReader(c.resolve("vlq_codec")))
container.register("cseq_writer", lambda c: CseqWriter(c.resolve("vlq_codec")))
container.register("vag_reader", lambda c: VagReader())
container.register("vag_writer", lambda c: VagWriter())
container.register("bank_reader", lambda c: BankReader())
container.register("cseq_editor", lambda c: CseqEditor(
    c.resolve("cseq_reader"),
    c.resolve("cseq_writer")
))
container.register("bank_builder", lambda c: BankBuilder(c.resolve("vag_reader")))
container.register("midi_converter", lambda c: MidiConverter(c.resolve("cseq_writer")))
container.register("midi_exporter", lambda c: CseqMidiExporter())
container.register("wav_writer", lambda c: WavWriter())
container.register("vag_decoder", lambda c: VagDecoder(c.resolve("wav_writer")))
container.register("adsr_decoder", lambda c: AdsrDecoder())
container.register("pitch_calculator", lambda c: PitchCalculator())
container.register("gain_calculator", lambda c: GainCalculator())
container.register("cseq_renderer", lambda c: CseqRenderer(
    c.resolve("vag_decoder"),
    c.resolve("adsr_decoder"),
    c.resolve("wav_writer"),
    c.resolve("pitch_calculator"),
    c.resolve("gain_calculator")))
container.register("audio_player", lambda c: AudioPlayer())
container.register("sample_lookup", lambda c: SampleLookup(
    c.resolve("bank_reader"),
    c.resolve("cseq_reader")
))
container.register("version_detector", lambda c: HowlVersionDetector())
container.register("sample_classifier", lambda c: SampleClassifier(c.resolve("cseq_reader")))
container.register("validator", lambda c: BankCseqValidator(
    c.resolve("bank_reader"), 
    c.resolve("cseq_reader")))
container.register("batch_exporter", lambda c: BatchExporter(
    c.resolve("bank_reader"),
    c.resolve("cseq_reader"),
    c.resolve("vag_writer"),
    c.resolve("vag_decoder"),
    c.resolve("sample_classifier"),
    c.resolve("midi_exporter"),
))
container.register("template_engine", lambda c: TemplateEngine(_TEMPLATE_DIR))
container.register("howl_detail_formatter", lambda c: HowlDetailFormatter(
    c.resolve("version_detector"),
    c.resolve("template_engine")))
container.register("fx_detail_formatter", lambda c: FxDetailFormatter(c.resolve("template_engine")))
container.register("bank_detail_formatter", lambda c: BankDetailFormatter(
    c.resolve("bank_reader"),
    c.resolve("template_engine")))
container.register("song_detail_formatter", lambda c: SongDetailFormatter(
    c.resolve("cseq_reader"),
    c.resolve("template_engine")))
container.register("detail_formatter", lambda c: DetailFormatter(
    c.resolve("howl_detail_formatter"),
    c.resolve("fx_detail_formatter"),
    c.resolve("bank_detail_formatter"),
    c.resolve("song_detail_formatter"),
))
container.register("sca_chunk_reader", lambda c: ScaChunkReader())
container.register("sca_chunk_writer", lambda c: ScaChunkWriter())
container.register("sca_metadata_codec", lambda c: ScaMetadataCodec())
container.register("sca_reader", lambda c: ScaReader(
    c.resolve("sca_chunk_reader"),
    c.resolve("sca_metadata_codec"),
))
container.register("sca_writer", lambda c: ScaWriter(
    c.resolve("sca_chunk_writer"),
    c.resolve("sca_metadata_codec"),
))
container.register("sample_sizes_extractor", lambda c: SampleSizesExtractor(c.resolve("bank_reader")))
