from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform
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


UNITS = ["", "OZ", "LB", "ITEM", "KG", "G", "LIT", "ML", "GAL", "QT", "PT", "TSP", "TBSP"]
IMAGE_ROTATION_DEGREES = 90


class PrefillWorker(QObject):
    finished = pyqtSignal(object, str)
    failed = pyqtSignal(str, str)

    def __init__(self, service: OpenAIPrefillService, image_path: Path):
        super().__init__()
        self.service = service
        self.image_path = image_path

    def run(self) -> None:
        started = time.perf_counter()
        print(f"[labeler] worker start: {self.image_path.name}", flush=True)
        try:
            record = self.service.extract(self.image_path)
            elapsed = time.perf_counter() - started
            print(f"[labeler] worker success: {self.image_path.name} ({elapsed:.2f}s)", flush=True)
            self.finished.emit(record, self.image_path.name)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(
                f"[labeler] worker failed: {self.image_path.name} ({elapsed:.2f}s): {exc}",
                flush=True,
            )
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
        self.prefill_worker: PrefillWorker | None = None
        self.prefill_target: str | None = None

        self.setWindowTitle("Price Tag Labeler")
        self.resize(1200, 900)
        self._build_ui()
        self._run_openai_smoke_test()

        if not self.image_paths:
            QMessageBox.warning(self, "No Images", f"No images found in {self.images_dir}")
        else:
            self.load_current_image()

    def _run_openai_smoke_test(self) -> None:
        print("[labeler] running OpenAI startup smoke test", flush=True)
        try:
            self.prefill_service.smoke_test()
            self.status_label.setText("OpenAI connection OK.")
        except Exception as exc:
            self.status_label.setText("OpenAI connection failed.")
            QMessageBox.warning(
                self,
                "OpenAI Connection Failed",
                (
                    "Failed OpenAI startup smoke test. Prefill may not work until fixed.\n\n"
                    f"{exc}"
                ),
            )

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
        self.variable_weight_input = QCheckBox("Variable weight item")
        self.ambiguous_input = QCheckBox("Ambiguous image (multiple plausible tags)")
        self.unparsable_input = QCheckBox("Unparsable image (cannot reliably read tag)")
        self.upc_present_input = QCheckBox("UPC present")
        self.upc_code_input = QLineEdit()
        self.status_label = QLabel("")

        form.addRow("Price", self.price_input)
        form.addRow("Net quantity", self.net_quantity_input)
        form.addRow("Quantity unit", self.quantity_unit_input)
        form.addRow("Pack count", self.pack_count_input)
        form.addRow("", self.variable_weight_input)
        form.addRow("", self.ambiguous_input)
        form.addRow("", self.unparsable_input)
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
        self.ambiguous_input.toggled.connect(self._on_quality_flag_toggled)
        self.unparsable_input.toggled.connect(self._on_quality_flag_toggled)
        self.variable_weight_input.toggled.connect(self._on_variable_weight_toggled)

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
        print(
            f"[labeler] loading image {self.current_index + 1}/{len(self.image_paths)}: {image_path.name}",
            flush=True,
        )
        self.index_label.setText(
            f"{self.current_index + 1} / {len(self.image_paths)}  |  {image_path.name}"
        )
        self._render_image(image_path)
        self._load_record(image_path.name)
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.image_paths) - 1)

    def _render_image(self, image_path: Path) -> None:
        # UI always renders from the original file; upload downscaling is handled separately.
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText(f"Unable to load image: {image_path.name}")
            return
        pixmap = pixmap.transformed(
            QTransform().rotate(IMAGE_ROTATION_DEGREES),
            Qt.TransformationMode.SmoothTransformation,
        )
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
        normalized_unit = self._normalize_quantity_unit(record.quantity_unit)
        self.quantity_unit_input.setCurrentText(normalized_unit or "")
        self.pack_count_input.setText("" if record.pack_count is None else str(record.pack_count))
        self.variable_weight_input.setChecked(record.is_variable_weight)
        self._set_quality_flags(record.is_ambiguous, record.is_unparsable)
        self.upc_present_input.setChecked(record.upc_present and not self._is_quality_flagged())
        self.upc_code_input.setText(record.upc_code or "")
        if self._is_quality_flagged():
            self._on_quality_flag_toggled(True)
        self._update_parsing_fields_enabled()

    def _clear_fields(self) -> None:
        self.price_input.clear()
        self.net_quantity_input.clear()
        self.quantity_unit_input.setCurrentText("")
        self.pack_count_input.clear()
        self.variable_weight_input.setChecked(False)
        self._set_quality_flags(False, False)
        self.upc_present_input.setChecked(False)
        self.upc_code_input.clear()
        self._update_parsing_fields_enabled()

    def prefill_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        if self.prefill_thread is not None:
            print(f"[labeler] prefill ignored (already in progress): {image_path.name}", flush=True)
            return

        print(f"[labeler] prefill queued: {image_path.name}", flush=True)
        self.status_label.setText("Prefilling from OpenAI...")
        self.prefill_target = image_path.name
        worker = PrefillWorker(self.prefill_service, image_path)
        thread = QThread(self)
        self.prefill_worker = worker
        worker.moveToThread(thread)
        thread.started.connect(
            lambda: print(f"[labeler] thread started: {image_path.name}", flush=True)
        )
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
            print(
                f"[labeler] prefill finished for stale image {filename}; current is {self.image_paths[self.current_index].name}",
                flush=True,
            )
            return
        print(f"[labeler] prefill finished: {filename}", flush=True)
        self._populate_fields(record)
        self.status_label.setText("Prefill complete. Review and submit.")

    def _on_prefill_failed(self, message: str, filename: str) -> None:
        if filename != self.image_paths[self.current_index].name:
            print(
                f"[labeler] prefill failed for stale image {filename}; current is {self.image_paths[self.current_index].name}",
                flush=True,
            )
            return
        print(f"[labeler] prefill failed: {filename}: {message}", flush=True)
        self.status_label.setText(f"Prefill failed: {message}")

    def _clear_prefill_thread(self) -> None:
        self.prefill_thread = None
        self.prefill_worker = None

    def submit_current(self) -> None:
        image_path = self.image_paths[self.current_index]
        is_ambiguous = self.ambiguous_input.isChecked()
        is_unparsable = self.unparsable_input.isChecked()
        if is_ambiguous or is_unparsable:
            record = PriceTagRecord(
                image_filename=image_path.name,
                status="flagged",
                is_ambiguous=is_ambiguous,
                is_unparsable=is_unparsable,
                prefilled_by_model=False,
            )
            self.dataset_store.upsert(record)
            self.status_label.setText("Saved flags.")
            self.go_next()
            return

        record = PriceTagRecord(
            image_filename=image_path.name,
            status="labeled",
            is_ambiguous=False,
            is_unparsable=False,
            is_variable_weight=self.variable_weight_input.isChecked(),
            price=self._optional_float(self.price_input.text()),
            net_quantity=self._optional_float(self.net_quantity_input.text()),
            quantity_unit=self.quantity_unit_input.currentText() or None,
            pack_count=(
                None if self.variable_weight_input.isChecked()
                else self._optional_int(self.pack_count_input.text())
            ),
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

    def _set_quality_flags(self, is_ambiguous: bool, is_unparsable: bool) -> None:
        self.ambiguous_input.blockSignals(True)
        self.unparsable_input.blockSignals(True)
        self.ambiguous_input.setChecked(is_ambiguous)
        self.unparsable_input.setChecked(is_unparsable)
        self.ambiguous_input.blockSignals(False)
        self.unparsable_input.blockSignals(False)

    def _is_quality_flagged(self) -> bool:
        return self.ambiguous_input.isChecked() or self.unparsable_input.isChecked()

    def _on_quality_flag_toggled(self, _: bool) -> None:
        flagged = self._is_quality_flagged()
        if flagged:
            self.price_input.clear()
            self.net_quantity_input.clear()
            self.quantity_unit_input.setCurrentText("")
            self.pack_count_input.clear()
            self.variable_weight_input.setChecked(False)
            self.upc_present_input.setChecked(False)
            self.upc_code_input.clear()
            self.status_label.setText("Flagged image: fields cleared; only flags will be saved.")
        self._update_parsing_fields_enabled()

    def _on_variable_weight_toggled(self, checked: bool) -> None:
        if checked:
            self.pack_count_input.clear()
        self._update_parsing_fields_enabled()

    def _update_parsing_fields_enabled(self) -> None:
        enabled = not self._is_quality_flagged()
        self.price_input.setEnabled(enabled)
        self.net_quantity_input.setEnabled(enabled)
        self.quantity_unit_input.setEnabled(enabled)
        self.variable_weight_input.setEnabled(enabled)
        self.pack_count_input.setEnabled(enabled and not self.variable_weight_input.isChecked())
        self.upc_present_input.setEnabled(enabled)
        self.upc_code_input.setEnabled(enabled)
        self.prefill_button.setEnabled(enabled)

    def _normalize_quantity_unit(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized == "EA":
            return "ITEM"
        return normalized


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
