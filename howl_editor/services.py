# coding: utf-8

from howl_editor.analysis.sample_classifier import SampleClassifier
from howl_editor.analysis.validator import BankCseqValidator
from howl_editor.audio.cseq_renderer import CseqRenderer
from howl_editor.audio.player import AudioPlayer
from howl_editor.audio.vag_decoder import VagDecoder
from howl_editor.bank.builder import BankBuilder
from howl_editor.bank.reader import BankReader
from howl_editor.core import Container
from howl_editor.cseq.editor import CseqEditor
from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.export.batch_exporter import BatchExporter
from howl_editor.howl.editor import HowlEditor
from howl_editor.howl.reader import HowlReader
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.howl.writer import HowlWriter
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.exporter import CseqMidiExporter
from howl_editor.vag.reader import VagReader
from howl_editor.vag.writer import VagWriter

container = Container()
container.register("howl_reader", lambda c: HowlReader())
container.register("howl_writer", lambda c: HowlWriter())
container.register("howl_editor", lambda c: HowlEditor())
container.register("cseq_reader", lambda c: CseqReader())
container.register("cseq_writer", lambda c: CseqWriter())
container.register("vag_reader", lambda c: VagReader())
container.register("vag_writer", lambda c: VagWriter())
container.register("bank_reader", lambda c: BankReader())
container.register("cseq_editor", lambda c: CseqEditor(c.resolve("cseq_reader"), c.resolve("cseq_writer")))
container.register("bank_builder", lambda c: BankBuilder(c.resolve("vag_reader")))
container.register("midi_converter", lambda c: MidiConverter(c.resolve("cseq_writer")))
container.register("midi_exporter", lambda c: CseqMidiExporter())
container.register("vag_decoder", lambda c: VagDecoder())
container.register("cseq_renderer", lambda c: CseqRenderer(c.resolve("vag_decoder")))
container.register("audio_player", lambda c: AudioPlayer())
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
