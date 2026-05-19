# coding: utf-8

import sys

from PySide6.QtWidgets import QApplication

from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container

if __name__ == "__main__":
    app = QApplication(sys.argv)

    stylesheet_loader = container.resolve("stylesheet_loader")
    app.setStyleSheet(stylesheet_loader.load("app.qss"))

    window = MainWindow(
        howl_reader=container.resolve("howl_reader"),
        howl_writer=container.resolve("howl_writer"),
        howl_editor_svc=container.resolve("howl_editor"),
        cseq_reader=container.resolve("cseq_reader"),
        cseq_writer=container.resolve("cseq_writer"),
        cseq_editor=container.resolve("cseq_editor"),
        vag_reader=container.resolve("vag_reader"),
        vag_writer=container.resolve("vag_writer"),
        bank_reader=container.resolve("bank_reader"),
        bank_builder=container.resolve("bank_builder"),
        midi_converter=container.resolve("midi_converter"),
        midi_exporter=container.resolve("midi_exporter"),
        vag_decoder=container.resolve("vag_decoder"),
        cseq_renderer=container.resolve("cseq_renderer"),
        audio_player=container.resolve("audio_player"),
        resampler=container.resolve("resampler"),
        wav_writer=container.resolve("wav_writer"),
        audio_cache=container.resolve("audio_cache"),
        sample_lookup=container.resolve("sample_lookup"),
        version_detector=container.resolve("version_detector"),
        sample_classifier=container.resolve("sample_classifier"),
        validator=container.resolve("validator"),
        batch_exporter=container.resolve("batch_exporter"),
        detail_formatter=container.resolve("detail_formatter"),
        sca_reader=container.resolve("sca_reader"),
        sca_writer=container.resolve("sca_writer"),
        sample_sizes_extractor=container.resolve("sample_sizes_extractor"),
        semantic_entry_builder=container.resolve("semantic_entry_builder"),
        entry_leaves_builder=container.resolve("entry_leaves_builder"),
        blob_snapshot=container.resolve("blob_snapshot"),
        entry_drop_router=container.resolve("entry_drop_router"),
        stylesheet_loader=stylesheet_loader,
        adventure_hub_mask_table_query=container.resolve("adventure_hub_mask_table_query"),
        category_icon_resolver=container.resolve("category_icon_resolver"),
        cseq_size_validator=container.resolve("cseq_size_validator"),
        drum_names=container.resolve("gm_drum_names"),
        leaf_info_formatter=container.resolve("leaf_info_formatter"),
        howl_stats_calculator=container.resolve("howl_stats_calculator"),
        size_formatter=container.resolve("size_formatter"),
    )

    window.show()
    sys.exit(app.exec())
