from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from price_tag_ai.dataset import PriceTagDatasetStore, PriceTagRecord, list_images
from price_tag_ai.openai_prefill import OpenAIPrefillService


UNITS = ["", "OZ", "LB", "EA", "KG", "G", "LIT", "ML", "GAL", "QT", "PT"]


class PrefillWorker(QObject):
    finished = pyqtSignal(object, str)
    failed = pyqtSignal(str, str)

    def __init__(self, service: OpenAIPrefillService, image_path: Path):
        super().__init__()
        self.service = service
        self.image_path = image_path

    def run(self) -> None:
        try:
            record = self.service.extract(self.image_path)
            self.finished.emit(record, self.image_path.name)
        except Exception as exc:
            self.failed.emit(str(exc), self.image_path.name)


class LabelerWindow(QMainWindow):
    def __init__(
        self,
        images_dir: str | Path,
        dataset_path: str | Path,
        prefill_service: OpenAIPrefillService | None = None,
    ):
        super().__init__()
        self.images_dir = Path(images_dir)
        self.dataset_store = PriceTagDatasetStore(dataset_path)
        self.prefill_service = prefill_service or OpenAIPrefillService()
        self.image_paths = list_images(self.images_dir)
        self.current_index = 0
        self.prefill_thread: QThread | None = None
        self.prefill_target: str | None = None

        self.setWindowTitle("Price Tag Labeler")
        self.resize(1200, 900)
        self._build_ui()

        if not self.image_paths:
            QMessageBox.warning(self, "No Images", f"No images found in {self.images_dir}")
        else:
            self.load_current_image()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        self.index_label = QLabel("")
        root.addWidget(self.index_label)

        body = QHBoxLayout()
        root.addLayout(body, stretch=1)

        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(700, 700)
        body.addWidget(self.image_label, stretch=3)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form = QFormLayout()

        self.price_input = QLineEdit()
        self.net_quantity_input = QLineEdit()
        self.quantity_unit_input = QComboBox()
        self.quantity_unit_input.addItems(UNITS)
        self.pack_count_input = QLineEdit()
        self.upc_present_input = QCheckBox("UPC present")
        self.upc_code_input = QLineEdit()
        self.status_label = QLabel("")

        form.addRow("Price", self.price_input)
        form.addRow("Net quantity", self.net_quantity_input)
        form.addRow("Quantity unit", self.quantity_unit_input)
        form.addRow("Pack count", self.pack_count_input)
        form.addRow("", self.upc_present_input)
        form.addRow("UPC code", self.upc_code_input)
        form_layout.addLayout(form)
        form_layout.addWidget(self.status_label)
        form_layout.addStretch(1)
        body.addWidget(form_container, stretch=2)

        buttons = QHBoxLayout()
        root.addLayout(buttons)

        self.back_button = QPushButton("Back")
        self.next_button = QPushButton("Next")
        self.prefill_button = QPushButton("Prefill")
        self.submit_button = QPushButton("Submit")
        self.skip_button = QPushButton("Skip")
        self.trash_button = QPushButton("Trash")

        self.back_button.clicked.connect(self.go_back)
        self.next_button.clicked.connect(self.go_next)
        self.prefill_button.clicked.connect(self.prefill_current)
        self.submit_button.clicked.connect(self.submit_current)
        self.skip_button.clicked.connect(self.skip_current)
        self.trash_button.clicked.connect(self.trash_current)

        for button in [
            self.back_button,
            self.next_button,
            self.prefill_button,
            self.submit_button,
            self.skip_button,
            self.trash_button,
        ]:
            buttons.addWidget(button)

        self.setCentralWidget(central)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self.image_paths:
            self._render_image(self.image_paths[self.current_index])

    def load_current_image(self) -> None:
        image_path = self.image_paths[self.current_index]
        self.index_label.setText(
            f"{self.current_index + 1} / {len(self.image_paths)}  |  {image_path.name}"
        )
        self._render_image(image_path)
        self._load_record(image_path.name)
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.image_paths) - 1)

    def _render_image(self, image_path: Path) -> None:
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText(f"Unable to load image: {image_path.name}")
            return
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def _load_record(self, filename: str) -> None:
        self._clear_fields()
        record = self.dataset_store.get(filename)
        if record is not None:
            self._populate_fields(record)
            self.status_label.setText(f"Existing entry: {record.status}")
        else:
            self.status_label.setText("New image. Requesting OpenAI prefill...")
            self.prefill_current()

    def _populate_fields(self, record: PriceTagRecord) -> None:
        self.price_input.setText("" if record.price is None else str(record.price))
        self.net_quantity_input.setText(
            "" if record.net_quantity is None else str(record.net_quantity)
        )
        self.quantity_unit_input.setCurrentText(record.quantity_unit or "")
        self.pack_count_input.setText("" if record.pack_count is None else str(record.pack_count))
        self.upc_present_input.setChecked(record.upc_present)
        self.upc_code_input.setText(record.upc_code or "")

    def _clear_fields(self) -> None:
        self.price_input.clear()
        self.net_quantity_input.clear()
        self.quantity_unit_input.setCurrentText("")
        self.pack_count_input.clear()
        self.upc_present_input.setChecked(False)
        self.upc_code_input.clear()

    def prefill_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        if self.prefill_thread is not None:
            return

        self.status_label.setText("Prefilling from OpenAI...")
        self.prefill_target = image_path.name
        worker = PrefillWorker(self.prefill_service, image_path)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_prefill_finished)
        worker.failed.connect(self._on_prefill_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_prefill_thread)
        self.prefill_thread = thread
        thread.start()

    def _on_prefill_finished(self, record: PriceTagRecord, filename: str) -> None:
        if filename != self.image_paths[self.current_index].name:
            return
        self._populate_fields(record)
        self.status_label.setText("Prefill complete. Review and submit.")

    def _on_prefill_failed(self, message: str, filename: str) -> None:
        if filename != self.image_paths[self.current_index].name:
            return
        self.status_label.setText(f"Prefill failed: {message}")

    def _clear_prefill_thread(self) -> None:
        self.prefill_thread = None

    def submit_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        record = PriceTagRecord(
            image_filename=image_path.name,
            status="labeled",
            price=self._optional_float(self.price_input.text()),
            net_quantity=self._optional_float(self.net_quantity_input.text()),
            quantity_unit=self.quantity_unit_input.currentText() or None,
            pack_count=self._optional_int(self.pack_count_input.text()),
            upc_present=self.upc_present_input.isChecked(),
            upc_code=self.upc_code_input.text().strip() or None,
            prefilled_by_model=False,
        )
        if not record.upc_present:
            record.upc_code = None
        self.dataset_store.upsert(record)
        self.status_label.setText("Saved.")
        self.go_next()

    def skip_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        self.dataset_store.upsert(
            PriceTagRecord(
                image_filename=image_path.name,
                status="skipped",
            )
        )
        self.status_label.setText("Skipped.")
        self.go_next()

    def trash_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        self.dataset_store.upsert(
            PriceTagRecord(
                image_filename=image_path.name,
                status="trashed",
            )
        )
        self.status_label.setText("Marked as trashed.")
        self.go_next()

    def go_back(self) -> None:
        if self.current_index <= 0:
            return
        self.current_index -= 1
        self.load_current_image()

    def go_next(self) -> None:
        if self.current_index >= len(self.image_paths) - 1:
            return
        self.current_index += 1
        self.load_current_image()

    def _optional_float(self, value: str) -> float | None:
        stripped = value.strip()
        return float(stripped) if stripped else None

    def _optional_int(self, value: str) -> int | None:
        stripped = value.strip()
        return int(stripped) if stripped else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--dataset", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = QApplication(sys.argv)
    window = LabelerWindow(args.images_dir, args.dataset)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
