from __future__ import annotations

import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import torch
from PIL import Image

from db_server.parsing import TorchCheckpointPriceTagParser


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai_server"
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))


class TorchCheckpointPriceTagParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_compile = os.environ.get("GROCERY_AI_COMPILE")
        os.environ["GROCERY_AI_COMPILE"] = "0"

    def tearDown(self) -> None:
        if self._previous_compile is None:
            os.environ.pop("GROCERY_AI_COMPILE", None)
        else:
            os.environ["GROCERY_AI_COMPILE"] = self._previous_compile

    def test_loads_custom_trainer_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint_path = root / "custom.pt"
            self._write_custom_checkpoint(checkpoint_path)

            parser = TorchCheckpointPriceTagParser(checkpoint_path)
            result = parser.parse(self._sample_image_bytes(), "sample.jpg")

            self.assertIsNotNone(result.price_total)
            self.assertIsNotNone(result.net_quantity)

    def test_loads_hf_trainer_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint_path = root / "hf.pt"
            self._write_hf_checkpoint(checkpoint_path)

            parser = TorchCheckpointPriceTagParser(checkpoint_path)
            result = parser.parse(self._sample_image_bytes(), "sample.jpg")

            self.assertIsNotNone(result.price_total)
            self.assertIsNotNone(result.net_quantity)

    def test_reloads_checkpoint_after_file_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint_path = root / "reload.pt"
            self._write_custom_checkpoint(checkpoint_path)

            parser = TorchCheckpointPriceTagParser(checkpoint_path)
            parser.parse(self._sample_image_bytes(), "sample.jpg")
            initial_generation = parser._load_generation

            time.sleep(0.01)
            self._write_hf_checkpoint(checkpoint_path)
            parser.parse(self._sample_image_bytes(), "sample.jpg")

            self.assertGreater(parser._load_generation, initial_generation)

    def _sample_image_bytes(self) -> bytes:
        image = Image.new("RGB", (64, 64), "white")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()

    def _write_custom_checkpoint(self, checkpoint_path: Path) -> None:
        from price_tag_ai.config import AppConfig
        from price_tag_ai.train import PriceTagModel

        config = AppConfig.model_validate(
            {
                "model": {
                    "backbone": "mobilenet_v3_small",
                    "pretrained": False,
                    "image_size": 224,
                    "dropout": 0.1,
                }
            }
        )
        model = PriceTagModel(
            backbone=config.model.backbone,
            dropout=config.model.dropout,
            pretrained=False,
        )
        checkpoint = {
            "epoch": 1,
            "trainer_type": "custom",
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": {},
            "scheduler_state_dict": {},
            "config": config.model_dump(mode="json"),
            "units": [],
            "val_metrics": {},
        }
        torch.save(checkpoint, checkpoint_path)

    def _write_hf_checkpoint(self, checkpoint_path: Path) -> None:
        from price_tag_ai.config import AppConfig
        from price_tag_ai.train_hf import HFPriceTagModel

        config = AppConfig.model_validate(
            {
                "model": {
                    "backbone": "mobilenet_v3_small",
                    "hf_model_name": "google/vit-base-patch16-224-in21k",
                    "pretrained": False,
                    "image_size": 224,
                    "dropout": 0.1,
                }
            }
        )
        model = HFPriceTagModel(
            config=config,
            binary_pos_weights={
                "is_variable_weight": 1.0,
                "is_ambiguous": 1.0,
                "is_unparsable": 1.0,
                "upc_present": 1.0,
            },
            load_pretrained_encoder=False,
        )
        checkpoint = {
            "epoch": 1,
            "trainer_type": "hf",
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": {},
            "scheduler_state_dict": {},
            "config": config.model_dump(mode="json"),
            "units": [],
            "val_metrics": {},
        }
        torch.save(checkpoint, checkpoint_path)
