from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from price_tag_ai.dataset import PriceTagDatasetStore, PriceTagRecord, list_images


class PriceTagDatasetStoreTest(unittest.TestCase):
    def test_upsert_and_reload_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "dataset.json"
            store = PriceTagDatasetStore(dataset_path)
            store.upsert(
                PriceTagRecord(
                    image_filename="image-1.jpg",
                    status="labeled",
                    price=4.99,
                    quantity_unit="OZ",
                    pack_count=1,
                    upc_present=True,
                    upc_code="123456789012",
                )
            )

            reloaded = PriceTagDatasetStore(dataset_path)
            record = reloaded.get("image-1.jpg")

            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(4.99, record.price)
            self.assertEqual("123456789012", record.upc_code)

    def test_dataset_file_is_json_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "dataset.json"
            store = PriceTagDatasetStore(dataset_path)
            store.upsert(PriceTagRecord(image_filename="image-1.jpg"))

            payload = json.loads(dataset_path.read_text())

            self.assertIsInstance(payload, list)
            self.assertEqual("image-1.jpg", payload[0]["image_filename"])


class ImageListingTest(unittest.TestCase):
    def test_list_images_filters_and_sorts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "b.png").write_bytes(b"x")
            (directory / "a.jpg").write_bytes(b"x")
            (directory / "note.txt").write_text("ignore")

            result = list_images(directory)

            self.assertEqual(["a.jpg", "b.png"], [path.name for path in result])
