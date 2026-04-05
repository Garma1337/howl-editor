# coding: utf-8

import sys

from PySide6.QtWidgets import QApplication
from howl_editor.services import container
from howl_editor.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    window = MainWindow(
        howl_reader=container.resolve("howl_reader"),
        howl_writer=container.resolve("howl_writer"),
        howl_editor_svc=container.resolve("howl_editor"),
        cseq_reader=container.resolve("cseq_reader"),
        cseq_writer=container.resolve("cseq_writer"),
        vag_reader=container.resolve("vag_reader"),
        vag_writer=container.resolve("vag_writer"),
        bank_reader=container.resolve("bank_reader"),
        bank_builder=container.resolve("bank_builder"),
        midi_converter=container.resolve("midi_converter"),
    )

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
