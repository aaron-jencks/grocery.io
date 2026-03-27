from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import torch

from price_tag_ai.config import AppConfig, AugmentationConfig
from price_tag_ai.train import (
    AddGaussianNoise,
    ManifestRecord,
    PriceTagModel,
    PriceTagTorchDataset,
    build_augmentations,
    build_tensor_augmentations,
    collect_eligible_records,
    generate_splits,
    read_manifest,
)
from price_tag_ai.train_hf import compute_eval_metrics, price_tag_data_collator


class TrainPipelineDataTest(unittest.TestCase):
    def test_app_config_accepts_wandb_settings(self) -> None:
        config = AppConfig.model_validate(
            {
                "wandb": {
                    "enabled": True,
                    "entity": "demo-entity",
                    "project": "demo-project",
                }
            }
        )

        self.assertTrue(config.wandb.enabled)
        self.assertEqual("demo-entity", config.wandb.entity)
        self.assertEqual("demo-project", config.wandb.project)

    def test_model_builds_with_mobilenet_v3_small_backbone(self) -> None:
        model = PriceTagModel(
            backbone="mobilenet_v3_small",
            dropout=0.1,
            pretrained=False,
        )
        output = model(torch.zeros((2, 3, 224, 224), dtype=torch.float32))

        self.assertEqual((2,), tuple(output["price"].shape))
        self.assertEqual((2, 12), tuple(output["unit_logits"].shape))

    def test_hf_data_collator_stacks_batch(self) -> None:
        sample = {
            "image": torch.zeros((3, 8, 8), dtype=torch.float32),
            "price": torch.tensor(1.0, dtype=torch.float32),
            "price_mask": torch.tensor(True, dtype=torch.bool),
            "net_quantity": torch.tensor(2.0, dtype=torch.float32),
            "net_quantity_mask": torch.tensor(True, dtype=torch.bool),
            "pack_count": torch.tensor(1.0, dtype=torch.float32),
            "pack_count_mask": torch.tensor(True, dtype=torch.bool),
            "quantity_unit_index": torch.tensor(2, dtype=torch.long),
            "quantity_unit_mask": torch.tensor(True, dtype=torch.bool),
            "is_variable_weight": torch.tensor(0.0, dtype=torch.float32),
            "is_ambiguous": torch.tensor(0.0, dtype=torch.float32),
            "is_unparsable": torch.tensor(0.0, dtype=torch.float32),
            "upc_present": torch.tensor(1.0, dtype=torch.float32),
        }

        batch = price_tag_data_collator([sample, sample])

        self.assertEqual((2, 3, 8, 8), tuple(batch["images"].shape))
        self.assertEqual((2,), tuple(batch["price"].shape))

    def test_hf_compute_eval_metrics_returns_expected_keys(self) -> None:
        predictions = (
            torch.tensor([1.0, 2.0]).numpy(),
            torch.tensor([2.0, 3.0]).numpy(),
            torch.tensor([1.0, 1.0]).numpy(),
            torch.tensor([[0.1, 0.9], [0.8, 0.2]]).numpy(),
            torch.tensor([0.0, 1.0]).numpy(),
            torch.tensor([0.0, 0.0]).numpy(),
            torch.tensor([0.0, 0.0]).numpy(),
            torch.tensor([1.0, 1.0]).numpy(),
        )
        labels = (
            torch.tensor([1.0, 2.5]).numpy(),
            torch.tensor([True, True]).numpy(),
            torch.tensor([2.0, 4.0]).numpy(),
            torch.tensor([True, True]).numpy(),
            torch.tensor([1.0, 1.0]).numpy(),
            torch.tensor([True, True]).numpy(),
            torch.tensor([1, 0]).numpy(),
            torch.tensor([True, True]).numpy(),
            torch.tensor([0.0, 1.0]).numpy(),
            torch.tensor([0.0, 0.0]).numpy(),
            torch.tensor([0.0, 0.0]).numpy(),
            torch.tensor([1.0, 1.0]).numpy(),
        )

        metrics = compute_eval_metrics((predictions, labels))

        self.assertIn("price_mae", metrics)
        self.assertIn("unit_accuracy", metrics)
        self.assertIn("variable_weight_f1", metrics)

    def test_build_augmentations_includes_expected_train_transforms(self) -> None:
        augmentation = AugmentationConfig()

        transforms_list = build_augmentations(augmentation)
        transform_names = [type(transform).__name__ for transform in transforms_list]

        self.assertEqual(
            [
                "RandomRotation",
                "ColorJitter",
                "RandomPerspective",
                "RandomApply",
            ],
            transform_names,
        )

    def test_build_tensor_augmentations_adds_noise_only_when_enabled(self) -> None:
        enabled = build_tensor_augmentations(AugmentationConfig(noise_probability=0.5, noise_std=0.01))
        disabled = build_tensor_augmentations(AugmentationConfig(enabled=False))

        self.assertEqual(1, len(enabled))
        self.assertEqual("RandomApply", type(enabled[0]).__name__)
        self.assertEqual(0, len(disabled))
        self.assertIsInstance(enabled[0].transforms[0], AddGaussianNoise)

    def test_train_dataset_regenerates_augmentations_per_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_root = root / "images"
            image_root.mkdir(parents=True)
            image_path = image_root / "sample.jpg"
            Image.new("RGB", (32, 32), "white").save(image_path)

            record = ManifestRecord(
                image_filename="sample.jpg",
                price=1.0,
                net_quantity=1.0,
                pack_count=1.0,
                quantity_unit="ITEM",
                is_variable_weight=False,
                is_ambiguous=False,
                is_unparsable=False,
                upc_present=False,
            )
            dataset = PriceTagTorchDataset(
                records=[record],
                image_root=image_root,
                image_size=32,
                train=True,
                augmentation=AugmentationConfig(
                    enabled=True,
                    rotation_degrees=0.0,
                    brightness=0.0,
                    contrast=0.0,
                    blur_probability=0.0,
                    perspective_probability=0.0,
                    noise_probability=1.0,
                    noise_std=0.05,
                ),
            )

            first = dataset[0]["image"]
            second = dataset[0]["image"]

            self.assertFalse(torch.equal(first, second))

    def test_val_dataset_stays_deterministic_without_train_augmentations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_root = root / "images"
            image_root.mkdir(parents=True)
            image_path = image_root / "sample.jpg"
            Image.new("RGB", (32, 32), "white").save(image_path)

            record = ManifestRecord(
                image_filename="sample.jpg",
                price=1.0,
                net_quantity=1.0,
                pack_count=1.0,
                quantity_unit="ITEM",
                is_variable_weight=False,
                is_ambiguous=False,
                is_unparsable=False,
                upc_present=False,
            )
            dataset = PriceTagTorchDataset(
                records=[record],
                image_root=image_root,
                image_size=32,
                train=False,
                augmentation=AugmentationConfig(
                    enabled=True,
                    rotation_degrees=10.0,
                    brightness=0.5,
                    contrast=0.5,
                    blur_probability=1.0,
                    perspective_probability=1.0,
                    noise_probability=1.0,
                    noise_std=0.1,
                ),
            )

            first = dataset[0]["image"]
            second = dataset[0]["image"]

            self.assertTrue(torch.equal(first, second))

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
