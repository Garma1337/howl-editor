# coding: utf-8

import sys

from PySide6.QtWidgets import QApplication

from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container

if __name__ == "__main__":
    app = QApplication(sys.argv)

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
        sample_lookup=container.resolve("sample_lookup"),
        version_detector=container.resolve("version_detector"),
        sample_classifier=container.resolve("sample_classifier"),
        validator=container.resolve("validator"),
        batch_exporter=container.resolve("batch_exporter"),
        detail_formatter=container.resolve("detail_formatter"),
        sca_reader=container.resolve("sca_reader"),
        sca_writer=container.resolve("sca_writer"),
        sample_sizes_extractor=container.resolve("sample_sizes_extractor"),
    )

    window.show()
    sys.exit(app.exec())
