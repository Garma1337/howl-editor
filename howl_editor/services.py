# coding: utf-8

from pathlib import Path

from howl_editor.audio.audio_cache import AudioCache
from howl_editor.audio.audio_player import AudioPlayer
from howl_editor.audio.linear_interpolation_resampler import LinearInterpolationResampler
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.core import Container
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.analysis.howl_stats import HowlStatsCalculator
from howl_editor.ctr.analysis.sample_classifier import SampleClassifier
from howl_editor.ctr.analysis.stock_layout_resolver import StockLayoutResolver
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from howl_editor.ctr.analysis.validator import BankCseqValidator
from howl_editor.ctr.cseq_renderer import CseqRenderer
from howl_editor.ctr.formats.bank.builder import BankBuilder
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.adventure_hub_mask_table_query import AdventureHubMaskTableQuery
from howl_editor.ctr.formats.cseq.editor import CseqEditor
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator
from howl_editor.ctr.formats.cseq.track_mask_layout import TrackMaskLayout
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from howl_editor.ctr.formats.howl.blob_snapshot import BlobSnapshot
from howl_editor.ctr.formats.howl.editor import HowlEditor
from howl_editor.ctr.formats.howl.reader import HowlReader
from howl_editor.ctr.formats.howl.version import HowlVersionDetector
from howl_editor.ctr.formats.howl.writer import HowlWriter
from howl_editor.ctr.sample_lookup import SampleLookup
from howl_editor.ctr.voice.gain_calculator import GainCalculator
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.export.batch_exporter import BatchExporter
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.detail.bank_detail_formatter import BankDetailFormatter
from howl_editor.gui.detail.detail_formatter import DetailFormatter
from howl_editor.gui.detail.fx_detail_formatter import FxDetailFormatter
from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.gui.detail.leaf_info_formatter import LeafInfoFormatter
from howl_editor.gui.detail.song_detail_formatter import SongDetailFormatter
from howl_editor.gui.entries.blob_modification_detector import BlobModificationDetector
from howl_editor.gui.entries.entry_leaves_builder import EntryLeavesBuilder
from howl_editor.gui.entries.semantic_entry_builder import SemanticEntryBuilder
from howl_editor.gui.entry_drop_router import EntryDropRouter
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.drum_name_resolver import DrumNameResolver
from howl_editor.midi.drum_pitch_remapper import DrumPitchRemapper
from howl_editor.midi.exporter import CseqMidiExporter
from howl_editor.paths import RENDERED_SONG_CACHE_DIR
from howl_editor.ps1.adsr_decoder import AdsrDecoder
from howl_editor.ps1.formats.vag.decoder import VagDecoder
from howl_editor.ps1.formats.vag.reader import VagReader
from howl_editor.ps1.formats.vag.writer import VagWriter
from howl_editor.saphi.formats.sca.chunk_reader import ScaChunkReader
from howl_editor.saphi.formats.sca.chunk_writer import ScaChunkWriter
from howl_editor.saphi.formats.sca.metadata_codec import ScaMetadataCodec
from howl_editor.saphi.formats.sca.reader import ScaReader
from howl_editor.saphi.formats.sca.sample_sizes_extractor import SampleSizesExtractor
from howl_editor.saphi.formats.sca.writer import ScaWriter

_TEMPLATE_DIR = Path(__file__).parent / "gui" / "templates"
_QSS_DIR = _TEMPLATE_DIR / "qss"
_IMAGE_DIR = _TEMPLATE_DIR / "images"

container = Container()
container.register("vlq_codec", lambda c: VlqCodec())
container.register("stock_names", lambda c: StockNameResolver())
container.register("howl_reader", lambda c: HowlReader())
container.register("howl_writer", lambda c: HowlWriter())
container.register("howl_editor", lambda c: HowlEditor())
container.register("cseq_reader", lambda c: CseqReader(
    c.resolve("vlq_codec"), c.resolve("stock_names"),
))
container.register("cseq_writer", lambda c: CseqWriter(c.resolve("vlq_codec")))
container.register("cseq_size_validator", lambda c: CseqSizeValidator())
container.register("vag_reader", lambda c: VagReader())
container.register("vag_writer", lambda c: VagWriter())
container.register("bank_reader", lambda c: BankReader(c.resolve("stock_names")))
container.register("cseq_editor", lambda c: CseqEditor(
    c.resolve("cseq_reader"),
    c.resolve("cseq_writer")
))
container.register("bank_builder", lambda c: BankBuilder(c.resolve("vag_reader")))
container.register("drum_pitch_remapper", lambda c: DrumPitchRemapper())
container.register("gm_drum_names", lambda c: DrumNameResolver())
container.register("midi_converter", lambda c: MidiConverter(
    c.resolve("cseq_writer"),
    c.resolve("drum_pitch_remapper"),
))
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
container.register("resampler", lambda c: LinearInterpolationResampler())
container.register("audio_cache", lambda c: AudioCache(RENDERED_SONG_CACHE_DIR))
container.register("sample_lookup", lambda c: SampleLookup(
    c.resolve("bank_reader"),
    c.resolve("cseq_reader")
))
container.register("version_detector", lambda c: HowlVersionDetector())
container.register("sample_classifier", lambda c: SampleClassifier(c.resolve("cseq_reader")))
container.register("howl_stats_calculator", lambda c: HowlStatsCalculator())
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
container.register("size_formatter", lambda c: SizeFormatter())
container.register("howl_detail_formatter", lambda c: HowlDetailFormatter(
    c.resolve("version_detector"),
    c.resolve("template_engine"),
    c.resolve("size_formatter")))
container.register("fx_detail_formatter", lambda c: FxDetailFormatter(c.resolve("template_engine")))
container.register("leaf_info_formatter", lambda c: LeafInfoFormatter(
    c.resolve("template_engine"),
    c.resolve("bank_reader"),
    c.resolve("cseq_reader"),
    c.resolve("sample_lookup"),
    c.resolve("size_formatter"),
))
container.register("bank_detail_formatter", lambda c: BankDetailFormatter(
    c.resolve("bank_reader"),
    c.resolve("template_engine"),
    c.resolve("size_formatter")))
container.register("song_detail_formatter", lambda c: SongDetailFormatter(
    c.resolve("cseq_reader"),
    c.resolve("template_engine"),
    c.resolve("size_formatter")))
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
container.register("adventure_hub_mask_table_query", lambda c: AdventureHubMaskTableQuery())
container.register("track_mask_layout", lambda c: TrackMaskLayout())
container.register("entry_leaves_builder", lambda c: EntryLeavesBuilder(
    c.resolve("bank_reader"),
    c.resolve("cseq_reader"),
    c.resolve("track_mask_layout"),
))
container.register("stock_layout", lambda c: StockLayoutResolver())
container.register("blob_modification_detector", lambda c: BlobModificationDetector())
container.register("semantic_entry_builder", lambda c: SemanticEntryBuilder(
    c.resolve("bank_reader"),
    c.resolve("cseq_reader"),
    c.resolve("stock_layout"),
    c.resolve("blob_modification_detector"),
    c.resolve("adventure_hub_mask_table_query"),
))
container.register("blob_snapshot", lambda c: BlobSnapshot())
container.register("entry_drop_router", lambda c: EntryDropRouter())
container.register("stylesheet_loader", lambda c: StylesheetLoader(_QSS_DIR))
container.register("category_icon_resolver", lambda c: CategoryIconResolver(_IMAGE_DIR))
