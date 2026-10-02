# coding: utf-8

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container

if __name__ == "__main__":
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)

    stylesheet_loader = container.resolve("stylesheet_loader")
    app.setStyleSheet(stylesheet_loader.load("app.qss"))

    window = MainWindow(container)

    window.show()
    sys.exit(app.exec())
