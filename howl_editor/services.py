# coding: utf-8

from pathlib import Path

from howl_editor.core import Container
from howl_editor.paths import RENDERED_SONG_CACHE_DIR

_TEMPLATE_DIR = Path(__file__).parent / "gui" / "templates"
_QSS_DIR = _TEMPLATE_DIR / "qss"
_IMAGE_DIR = _TEMPLATE_DIR / "images"

container = Container()
container.register_lazy("vlq_codec", "howl_editor.core.vlq:VlqCodec")
container.register_lazy(
    "stock_names", "howl_editor.ctr.analysis.stock_name_resolver:StockNameResolver",
)
container.register_lazy("howl_reader", "howl_editor.ctr.formats.howl.reader:HowlReader")
container.register_lazy("howl_writer", "howl_editor.ctr.formats.howl.writer:HowlWriter")
container.register_lazy("howl_editor", "howl_editor.ctr.formats.howl.editor:HowlEditor")
container.register_lazy(
    "cseq_reader", "howl_editor.ctr.formats.cseq.reader:CseqReader",
    "vlq_codec",
    "stock_names",
)
container.register_lazy(
    "cseq_writer", "howl_editor.ctr.formats.cseq.writer:CseqWriter",
    "vlq_codec",
)
container.register_lazy("cseq_blob_cache", "howl_editor.core.blob_cache:BlobCache")
container.register_lazy(
    "cseq_parses", "howl_editor.ctr.formats.cseq.parse_cache:CseqParseCache",
    "cseq_reader",
    "cseq_blob_cache",
)
container.register_lazy(
    "cseq_size_validator", "howl_editor.ctr.formats.cseq.size_validator:CseqSizeValidator",
)
container.register_lazy("vag_reader", "howl_editor.ps1.formats.vag.reader:VagReader")
container.register_lazy("vag_writer", "howl_editor.ps1.formats.vag.writer:VagWriter")
container.register_lazy(
    "bank_reader", "howl_editor.ctr.formats.bank.reader:BankReader",
    "stock_names",
)
container.register_lazy(
    "cseq_editor", "howl_editor.ctr.formats.cseq.editor:CseqEditor",
    "cseq_reader",
    "cseq_writer",
)
container.register_lazy(
    "spu_slot_guard", "howl_editor.ctr.diagnostics.spu_slot_guard:SpuSlotGuard",
)
container.register_lazy(
    "bank_builder", "howl_editor.ctr.formats.bank.builder:BankBuilder",
    "vag_reader",
    "spu_slot_guard",
)
container.register_lazy(
    "drum_pitch_remapper", "howl_editor.midi.drum_pitch_remapper:DrumPitchRemapper",
)
container.register_lazy("gm_drum_names", "howl_editor.midi.drum_name_resolver:DrumNameResolver")
container.register_lazy(
    "midi_converter", "howl_editor.midi.converter:MidiConverter",
    "cseq_writer",
    "drum_pitch_remapper",
)
container.register_lazy("midi_exporter", "howl_editor.midi.exporter:CseqMidiExporter")
container.register_lazy("wav_writer", "howl_editor.audio.wav_writer:WavWriter")
container.register_lazy(
    "vag_decoder", "howl_editor.ps1.formats.vag.decoder:VagDecoder",
    "wav_writer",
)
container.register_lazy("adsr_decoder", "howl_editor.ps1.adsr_decoder:AdsrDecoder")
container.register_lazy(
    "pitch_calculator", "howl_editor.ctr.voice.pitch_calculator:PitchCalculator",
)
container.register_lazy("pitch_stepper", "howl_editor.ctr.voice.pitch_stepper:PitchStepper")
container.register_lazy(
    "pitch_shifter", "howl_editor.ctr.formats.cseq.pitch_shifter:CseqPitchShifter",
    "cseq_reader",
    "cseq_writer",
    "pitch_stepper",
)
container.register_lazy("gain_calculator", "howl_editor.ctr.voice.gain_calculator:GainCalculator")
container.register_lazy(
    "cseq_renderer", "howl_editor.ctr.cseq_renderer:CseqRenderer",
    "vag_decoder",
    "adsr_decoder",
    "wav_writer",
    "pitch_calculator",
    "gain_calculator",
)
container.register_lazy("audio_player", "howl_editor.audio.audio_player:AudioPlayer")
container.register_lazy(
    "resampler", "howl_editor.audio.linear_interpolation_resampler:LinearInterpolationResampler",
)
container.register_lazy(
    "vag_rate_provider", "howl_editor.audio.vag_sample_rate_provider:VagSampleRateProvider",
)
container.register_lazy(
    "audio_cache", "howl_editor.audio.audio_cache:AudioCache",
    cache_dir=RENDERED_SONG_CACHE_DIR,
)
container.register_lazy(
    "sample_lookup", "howl_editor.ctr.sample_lookup:SampleLookup",
    "bank_reader",
    "cseq_parses",
)
container.register_lazy(
    "version_detector", "howl_editor.ctr.formats.howl.version:HowlVersionDetector",
)
container.register_lazy(
    "sample_classifier", "howl_editor.ctr.analysis.sample_classifier:SampleClassifier",
    "cseq_parses",
)
container.register_lazy(
    "howl_stats_calculator", "howl_editor.ctr.analysis.howl_stats:HowlStatsCalculator",
)
container.register_lazy(
    "validator", "howl_editor.ctr.analysis.validator:BankCseqValidator",
    "bank_reader",
    "cseq_reader",
)
container.register_lazy(
    "spu_residency_calculator", "howl_editor.ctr.diagnostics.spu_residency:SpuResidencyCalculator",
    "bank_reader",
)
container.register_lazy(
    "cseq_size_guard", "howl_editor.ctr.diagnostics.cseq_size_guard:CseqSizeGuard",
    "cseq_size_validator",
)
container.register_lazy(
    "bank_size_guard", "howl_editor.ctr.diagnostics.bank_size_guard:BankSizeGuard",
    "spu_residency_calculator",
    "stock_layout",
)
container.register_lazy(
    "howl_size_guard", "howl_editor.ctr.diagnostics.howl_size_guard:HowlSizeGuard",
)
container.register_lazy(
    "vag_structure_validator", "howl_editor.ps1.formats.vag.structure_validator:VagStructureValidator",
)
container.register_lazy(
    "pitch_ceiling_validator", "howl_editor.ctr.diagnostics.pitch_ceiling_validator:PitchCeilingValidator",
    "pitch_calculator",
)
container.register_lazy(
    "pitch_headroom_inspector", "howl_editor.ctr.voice.pitch_headroom:PitchHeadroomInspector",
    "pitch_calculator",
)
container.register_lazy("bank_slice_cache", "howl_editor.core.blob_cache:BlobCache")
container.register_lazy(
    "bank_slice_validator", "howl_editor.ctr.diagnostics.bank_slice_validator:BankSliceValidator",
    "bank_reader",
    "vag_structure_validator",
    "bank_slice_cache",
)
container.register_lazy(
    "spu_slot_usage", "howl_editor.ctr.analysis.spu_slot_usage:SpuSlotUsageResolver",
    "bank_reader",
    "cseq_parses",
)
container.register_lazy(
    "spu_slot_allocator", "howl_editor.ctr.analysis.spu_slot_allocator:SpuSlotAllocator",
    "spu_slot_usage",
)
container.register_lazy(
    "spu_slot_choices", "howl_editor.gui.spu_slot_choice_builder:SpuSlotChoiceBuilder",
    "bank_reader",
    "spu_slot_usage",
    "spu_slot_allocator",
)
container.register_lazy(
    "sample_ownership", "howl_editor.ctr.analysis.sample_ownership:SampleOwnershipResolver",
    "bank_reader",
)
container.register_lazy(
    "shared_sample_propagator", "howl_editor.ctr.formats.bank.shared_sample_propagator:SharedSamplePropagator",
    "bank_reader",
    "bank_builder",
    "sample_ownership",
)
container.register_lazy(
    "sample_replacement_planner", "howl_editor.ctr.analysis.sample_replacement_planner:SampleReplacementPlanner",
    "bank_reader",
    "bank_builder",
    "shared_sample_guard",
    "bank_size_guard",
)
container.register_lazy(
    "shared_sample_guard", "howl_editor.ctr.diagnostics.shared_sample_guard:SharedSampleGuard",
    "sample_ownership",
    "bank_slice_validator",
    "bank_reader",
)
container.register_lazy(
    "howl_diagnostics", "howl_editor.ctr.diagnostics.howl_diagnostics:HowlDiagnostics",
    "cseq_reader",
    "cseq_parses",
    "cseq_size_validator",
    "bank_reader",
    "spu_residency_calculator",
    "validator",
    "stock_layout",
    "howl_size_guard",
    "bank_slice_validator",
    "pitch_ceiling_validator",
)
container.register_lazy(
    "diagnostics_status_provider", "howl_editor.gui.diagnostics_status_provider:DiagnosticsStatusProvider",
    "howl_diagnostics",
    "howl_writer",
)
container.register_lazy(
    "severity_presenter", "howl_editor.gui.severity_presenter:SeverityPresenter",
)
container.register_lazy(
    "entry_badge_resolver", "howl_editor.gui.entry_badge_resolver:EntryBadgeResolver",
    "severity_presenter",
)
container.register_lazy(
    "diagnosis_banner_formatter", "howl_editor.gui.detail.diagnosis_banner_formatter:DiagnosisBannerFormatter",
    "template_engine",
    "severity_presenter",
)
container.register_lazy(
    "sfz_exporter", "howl_editor.export.sfz_exporter:SfzExporter",
    "cseq_reader",
    "bank_reader",
    "sample_lookup",
    "vag_decoder",
)
container.register_lazy(
    "batch_exporter", "howl_editor.export.batch_exporter:BatchExporter",
    "bank_reader",
    "cseq_reader",
    "vag_writer",
    "vag_decoder",
    "sample_classifier",
    "midi_exporter",
)
container.register_lazy(
    "template_engine", "howl_editor.core.template_engine:TemplateEngine",
    template_dir=_TEMPLATE_DIR,
)
container.register_lazy("size_formatter", "howl_editor.gui.size_formatter:SizeFormatter")
container.register_lazy(
    "howl_detail_formatter", "howl_editor.gui.detail.howl_detail_formatter:HowlDetailFormatter",
    "version_detector",
    "template_engine",
    "size_formatter",
)
container.register_lazy(
    "fx_detail_formatter", "howl_editor.gui.detail.fx_detail_formatter:FxDetailFormatter",
    "template_engine",
)
container.register_lazy(
    "leaf_info_formatter", "howl_editor.gui.detail.leaf_info_formatter:LeafInfoFormatter",
    "template_engine",
    "bank_reader",
    "cseq_reader",
    "sample_lookup",
    "size_formatter",
)
container.register_lazy(
    "bank_detail_formatter", "howl_editor.gui.detail.bank_detail_formatter:BankDetailFormatter",
    "bank_reader",
    "template_engine",
    "size_formatter",
)
container.register_lazy(
    "song_detail_formatter", "howl_editor.gui.detail.song_detail_formatter:SongDetailFormatter",
    "cseq_reader",
    "template_engine",
    "size_formatter",
)
container.register_lazy(
    "detail_formatter", "howl_editor.gui.detail.detail_formatter:DetailFormatter",
    "howl_detail_formatter",
    "fx_detail_formatter",
    "bank_detail_formatter",
    "song_detail_formatter",
)
container.register_lazy(
    "sca_chunk_reader", "howl_editor.saphi.formats.sca.chunk_reader:ScaChunkReader",
)
container.register_lazy(
    "sca_chunk_writer", "howl_editor.saphi.formats.sca.chunk_writer:ScaChunkWriter",
)
container.register_lazy(
    "sca_metadata_codec", "howl_editor.saphi.formats.sca.metadata_codec:ScaMetadataCodec",
)
container.register_lazy(
    "sca_reader", "howl_editor.saphi.formats.sca.reader:ScaReader",
    "sca_chunk_reader",
    "sca_metadata_codec",
)
container.register_lazy(
    "sca_writer", "howl_editor.saphi.formats.sca.writer:ScaWriter",
    "sca_chunk_writer",
    "sca_metadata_codec",
)
container.register_lazy(
    "sample_sizes_extractor", "howl_editor.saphi.formats.sca.sample_sizes_extractor:SampleSizesExtractor",
    "bank_reader",
)
container.register_lazy(
    "sca_spu_slot_validator", "howl_editor.saphi.formats.sca.spu_slot_validator:ScaSpuSlotValidator",
    "bank_reader",
    "cseq_reader",
    "spu_slot_guard",
)
container.register_lazy(
    "adventure_hub_mask_table_query",
    "howl_editor.ctr.formats.cseq.adventure_hub_mask_table_query:AdventureHubMaskTableQuery",
)
container.register_lazy(
    "track_mask_layout", "howl_editor.ctr.formats.cseq.track_mask_layout:TrackMaskLayout",
)
container.register_lazy(
    "entry_leaves_builder", "howl_editor.gui.entries.entry_leaves_builder:EntryLeavesBuilder",
    "bank_reader",
    "cseq_reader",
    "track_mask_layout",
)
container.register_lazy(
    "stock_layout", "howl_editor.ctr.analysis.stock_layout_resolver:StockLayoutResolver",
)
container.register_lazy(
    "blob_modification_detector", "howl_editor.gui.entries.blob_modification_detector:BlobModificationDetector",
)
container.register_lazy(
    "semantic_entry_builder", "howl_editor.gui.entries.semantic_entry_builder:SemanticEntryBuilder",
    "bank_reader",
    "cseq_reader",
    "stock_layout",
    "blob_modification_detector",
    "adventure_hub_mask_table_query",
)
container.register_lazy("blob_snapshot", "howl_editor.ctr.formats.howl.blob_snapshot:BlobSnapshot")
container.register_lazy("entry_drop_router", "howl_editor.gui.entry_drop_router:EntryDropRouter")
container.register_lazy(
    "stylesheet_loader", "howl_editor.gui.stylesheet_loader:StylesheetLoader",
    qss_dir=_QSS_DIR,
)
container.register_lazy(
    "category_icon_resolver", "howl_editor.gui.category_icon_resolver:CategoryIconResolver",
    image_dir=_IMAGE_DIR,
)
container.register_lazy("tasks", "howl_editor.gui.background.task_runner:TaskRunner")
container.register_lazy(
    "process_tasks", "howl_editor.gui.background.process_runner:ProcessTaskRunner",
)
