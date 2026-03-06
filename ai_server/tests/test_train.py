from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from price_tag_ai.config import AppConfig
from price_tag_ai.train import collect_eligible_records, generate_splits, read_manifest


class TrainPipelineDataTest(unittest.TestCase):
    def test_collect_eligible_records_filters_and_normalizes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_root = root / "images"
            image_root.mkdir(parents=True)
            labels_path = root / "labels.json"

            Image.new("RGB", (32, 32), "white").save(image_root / "a.jpg")
            Image.new("RGB", (32, 32), "white").save(image_root / "b.jpg")
            payload = [
                {
                    "image_filename": "a.jpg",
                    "status": "labeled",
                    "is_ambiguous": False,
                    "is_unparsable": False,
                    "quantity_unit": "EA",
                    "price": 2.5,
                },
                {
                    "image_filename": "b.jpg",
                    "status": "flagged",
                    "is_ambiguous": True,
                    "is_unparsable": False,
                    "quantity_unit": None,
                },
            ]
            labels_path.write_text(json.dumps(payload))

            config = AppConfig.model_validate(
                {
                    "dataset": {
                        "labels_path": str(labels_path),
                        "image_root": str(image_root),
                        "train_manifest": str(root / "manifests/train.jsonl"),
                        "val_manifest": str(root / "manifests/val.jsonl"),
                    },
                    "train": {"seed": 42},
                }
            )
            records = collect_eligible_records(config)

            self.assertEqual(2, len(records))
            self.assertEqual("ITEM", records[0].quantity_unit)
            self.assertTrue(any(record.is_ambiguous for record in records))

    def test_generate_splits_writes_train_and_val(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_root = root / "images"
            image_root.mkdir(parents=True)
            labels_path = root / "labels.json"
            for i in range(5):
                Image.new("RGB", (32, 32), "white").save(image_root / f"{i}.jpg")
            payload = [
                {
                    "image_filename": f"{i}.jpg",
                    "status": "labeled",
                    "is_ambiguous": False,
                    "is_unparsable": False,
                    "quantity_unit": "ITEM",
                    "price": float(i + 1),
                }
                for i in range(5)
            ]
            labels_path.write_text(json.dumps(payload))

            train_manifest = root / "manifests/train.jsonl"
            val_manifest = root / "manifests/val.jsonl"
            config = AppConfig.model_validate(
                {
                    "dataset": {
                        "labels_path": str(labels_path),
                        "image_root": str(image_root),
                        "train_manifest": str(train_manifest),
                        "val_manifest": str(val_manifest),
                        "val_ratio": 0.4,
                    },
                    "train": {"seed": 1},
                }
            )

            generate_splits(config, train_manifest, val_manifest)
            train_records = read_manifest(train_manifest)
            val_records = read_manifest(val_manifest)

            self.assertEqual(3, len(train_records))
            self.assertEqual(2, len(val_records))

    def test_generate_splits_keeps_flag_coverage_across_splits_when_possible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_root = root / "images"
            image_root.mkdir(parents=True)
            labels_path = root / "labels.json"
            for i in range(12):
                Image.new("RGB", (32, 32), "white").save(image_root / f"{i}.jpg")
            payload = []
            for i in range(12):
                payload.append(
                    {
                        "image_filename": f"{i}.jpg",
                        "status": "labeled",
                        "quantity_unit": "ITEM",
                        "is_variable_weight": i in {0, 1, 2, 3},
                        "is_ambiguous": i in {4, 5},
                        "is_unparsable": i in {6, 7},
                    }
                )
            labels_path.write_text(json.dumps(payload))

            train_manifest = root / "manifests/train.jsonl"
            val_manifest = root / "manifests/val.jsonl"
            config = AppConfig.model_validate(
                {
                    "dataset": {
                        "labels_path": str(labels_path),
                        "image_root": str(image_root),
                        "train_manifest": str(train_manifest),
                        "val_manifest": str(val_manifest),
                        "val_ratio": 0.25,
                    },
                    "train": {"seed": 1},
                }
            )

            generate_splits(config, train_manifest, val_manifest)
            train_records = read_manifest(train_manifest)
            val_records = read_manifest(val_manifest)

            self.assertGreaterEqual(sum(1 for r in train_records if r.is_variable_weight), 1)
            self.assertGreaterEqual(sum(1 for r in val_records if r.is_variable_weight), 1)
            self.assertGreaterEqual(sum(1 for r in train_records if r.is_ambiguous), 1)
            self.assertGreaterEqual(sum(1 for r in val_records if r.is_ambiguous), 1)
            self.assertGreaterEqual(sum(1 for r in train_records if r.is_unparsable), 1)
            self.assertGreaterEqual(sum(1 for r in val_records if r.is_unparsable), 1)
