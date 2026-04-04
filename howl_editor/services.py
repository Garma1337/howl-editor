# coding: utf-8

"""Default service definitions for the HOWL Editor."""

from howl_editor.core import Container
from howl_editor.howl.reader import HowlReader
from howl_editor.howl.writer import HowlWriter
from howl_editor.howl.editor import HowlEditor
from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.vag.reader import VagReader
from howl_editor.vag.writer import VagWriter
from howl_editor.bank.reader import BankReader
from howl_editor.bank.builder import BankBuilder
from howl_editor.midi.converter import MidiConverter

container = Container()
container.register("howl_reader", lambda c: HowlReader())
container.register("howl_writer", lambda c: HowlWriter())
container.register("howl_editor", lambda c: HowlEditor())
container.register("cseq_reader", lambda c: CseqReader())
container.register("cseq_writer", lambda c: CseqWriter())
container.register("vag_reader", lambda c: VagReader())
container.register("vag_writer", lambda c: VagWriter())
container.register("bank_reader", lambda c: BankReader())
container.register("bank_builder", lambda c: BankBuilder(c.resolve("vag_reader")))
container.register("midi_converter", lambda c: MidiConverter(c.resolve("cseq_writer")))
