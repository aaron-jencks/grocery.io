from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


class PriceTagRecord(BaseModel):
    image_filename: str
    status: str = "labeled"
    is_ambiguous: bool = False
    is_unparsable: bool = False
    is_variable_weight: bool = False
    price: float | None = None
    net_quantity: float | None = None
    quantity_unit: str | None = None
    pack_count: int | None = None
    upc_present: bool = False
    upc_code: str | None = None
    prefilled_by_model: bool = False


class PriceTagDatasetStore:
    def __init__(self, dataset_path: str | Path):
        self.dataset_path = Path(dataset_path)
        self._records: dict[str, PriceTagRecord] = {}
        self.load()

    def load(self) -> None:
        if not self.dataset_path.exists():
            self._records = {}
            return

        payload = json.loads(self.dataset_path.read_text())
        if not isinstance(payload, list):
            raise ValueError("Dataset file must contain a JSON list")

        records: dict[str, PriceTagRecord] = {}
        for item in payload:
            record = PriceTagRecord.model_validate(item)
            records[record.image_filename] = record
        self._records = records

    def save(self) -> None:
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [
            record.model_dump(mode="json", exclude_none=True)
            for record in sorted(self._records.values(), key=lambda value: value.image_filename)
        ]
        self.dataset_path.write_text(json.dumps(serialized, indent=2, sort_keys=True))

    def get(self, image_filename: str) -> PriceTagRecord | None:
        return self._records.get(image_filename)

    def upsert(self, record: PriceTagRecord) -> None:
        self._records[record.image_filename] = record
        self.save()

    def values(self) -> Iterable[PriceTagRecord]:
        return self._records.values()


def list_images(images_dir: str | Path) -> list[Path]:
    directory = Path(images_dir)
    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )
