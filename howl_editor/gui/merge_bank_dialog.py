# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QGroupBox,
    QAbstractItemView, QMessageBox, )

from howl_editor.models import BankSample, SpuAddrEntry


class MergeBankDialog(QDialog):

    def __init__(
        self,
        parent,
        target_samples: list[BankSample],
        source_samples: list[BankSample],
        spu_addrs: list[SpuAddrEntry],
        target_label: str = "Target",
        source_label: str = "Source",
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Merge Bank: {source_label} into {target_label}")
        self.resize(750, 550)

        self._spu_addrs = spu_addrs
        self._source_pool: list[BankSample] = list(source_samples)

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_panels(target_label, source_label))
        layout.addWidget(self._build_buttons())

        self._populate_result(target_samples, "target")
        self._populate_source()

    def _build_panels(self, target_label: str, source_label: str) -> QHBoxLayout:
        panels = QHBoxLayout()

        source_group = QGroupBox(f"Available ({source_label})")
        source_layout = QVBoxLayout()
        self._source_list = QListWidget()
        self._source_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        source_layout.addWidget(self._source_list)
        source_group.setLayout(source_layout)

        center = QVBoxLayout()
        center.addStretch()
        self._btn_add = QPushButton("Add \u2192")
        self._btn_add.clicked.connect(self._on_add)
        center.addWidget(self._btn_add)
        self._btn_replace = QPushButton("Replace \u2194")
        self._btn_replace.setToolTip("Replace selected result entry with selected source entry")
        self._btn_replace.clicked.connect(self._on_replace)
        center.addWidget(self._btn_replace)
        center.addStretch()

        result_group = QGroupBox(f"Result ({target_label})")
        result_layout = QVBoxLayout()
        self._result_list = QListWidget()
        self._result_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._result_list.setDragDropMode(QAbstractItemView.InternalMove)
        result_layout.addWidget(self._result_list)

        btn_row = QHBoxLayout()
        self._btn_up = QPushButton("\u2191 Up")
        self._btn_up.clicked.connect(self._on_move_up)
        btn_row.addWidget(self._btn_up)
        self._btn_down = QPushButton("\u2193 Down")
        self._btn_down.clicked.connect(self._on_move_down)
        btn_row.addWidget(self._btn_down)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)
        result_layout.addLayout(btn_row)
        result_group.setLayout(result_layout)

        panels.addWidget(source_group, 1)
        panels.addLayout(center)
        panels.addWidget(result_group, 1)
        return panels

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def _format_sample(self, sample: BankSample, origin: str) -> str:
        size = len(sample.data)
        tag = "T" if origin == "target" else "S"
        return f"[{tag}] SPU {sample.spu_index} ({size} bytes)"

    def _populate_result(self, samples: list[BankSample], origin: str) -> None:
        for sample in samples:
            item = QListWidgetItem(self._format_sample(sample, origin))
            item.setData(Qt.UserRole, sample)
            item.setData(Qt.UserRole + 1, origin)
            self._result_list.addItem(item)

    def _populate_source(self) -> None:
        self._source_list.clear()

        for sample in self._source_pool:
            item = QListWidgetItem(self._format_sample(sample, "source"))
            item.setData(Qt.UserRole, sample)
            self._source_list.addItem(item)

    def _on_add(self) -> None:
        for item in self._source_list.selectedItems():
            sample: BankSample = item.data(Qt.UserRole)
            result_item = QListWidgetItem(self._format_sample(sample, "source"))
            result_item.setData(Qt.UserRole, sample)
            result_item.setData(Qt.UserRole + 1, "source")
            self._result_list.addItem(result_item)

    def _on_replace(self) -> None:
        result_sel = self._result_list.selectedItems()
        source_sel = self._source_list.selectedItems()
        
        if len(result_sel) != 1 or len(source_sel) != 1:
            QMessageBox.information(
                self, "Replace",
                "Select exactly one entry in the result list and one in the source list.",
            )
        
            return

        source_sample: BankSample = source_sel[0].data(Qt.UserRole)
        target_item = result_sel[0]
        target_item.setData(Qt.UserRole, source_sample)
        target_item.setData(Qt.UserRole + 1, "source")
        target_item.setText(self._format_sample(source_sample, "source"))

    def _on_remove(self) -> None:
        for item in reversed(self._result_list.selectedItems()):
            self._result_list.takeItem(self._result_list.row(item))

    def _on_move_up(self) -> None:
        for item in self._result_list.selectedItems():
            row = self._result_list.row(item)
            
            if row > 0:
                taken = self._result_list.takeItem(row)
                self._result_list.insertItem(row - 1, taken)
                self._result_list.setCurrentItem(taken)

    def _on_move_down(self) -> None:
        selected = self._result_list.selectedItems()

        for item in reversed(selected):
            row = self._result_list.row(item)
            
            if row < self._result_list.count() - 1:
                taken = self._result_list.takeItem(row)
                self._result_list.insertItem(row + 1, taken)
                self._result_list.setCurrentItem(taken)

    def _on_accept(self) -> None:
        if self._result_list.count() == 0:
            QMessageBox.warning(self, "Empty Bank", "The result bank has no samples.")
            return

        self.accept()

    def get_result(self) -> list[BankSample]:
        samples = []

        for i in range(self._result_list.count()):
            item = self._result_list.item(i)
            samples.append(item.data(Qt.UserRole))
        
        return samples
