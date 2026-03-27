from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import os
import io
import queue
import threading
import traceback

from db_server.domain.upc import ProductUnit

import torch
from PIL import Image
from torchvision import transforms


@dataclass(frozen=True)
class ParsedPriceTag:
    ambiguous: bool
    unparsable: bool
    upc_parsable: bool
    upc: str | None = None
    price_total: float | None = None
    pack_count: int | None = None
    net_quantity: float | None = None
    quantity_unit: ProductUnit | None = None
    is_variable_weight: bool = False
    message: str | None = None


@dataclass
class _ParseTask:
    image_jpeg: bytes
    image_filename: str | None
    done: threading.Event
    result: ParsedPriceTag | None = None
    error: Exception | None = None


class PriceTagParser(Protocol):
    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        ...


class FallbackPriceTagParser:
    def __init__(self, reason: str):
        self.reason = reason

    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        _ = image_jpeg
        _ = image_filename
        return ParsedPriceTag(
            ambiguous=False,
            unparsable=True,
            upc_parsable=False,
            message=self.reason,
        )


class TorchCheckpointPriceTagParser:
    def __init__(self, checkpoint_path: Path):
        self._checkpoint_path = checkpoint_path
        project_root = Path(__file__).resolve().parent.parent
        ai_root = project_root / "ai_server"
        import sys
        if str(ai_root) not in sys.path:
            sys.path.insert(0, str(ai_root))
        from price_tag_ai.train import UNITS

        self._units: list[str] = list(UNITS)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._task_queue: queue.Queue[_ParseTask | None] = queue.Queue()
        self._checkpoint_mtime_ns: int | None = None
        self._model = None
        self._forward_image_key = "images"
        self._transform = None
        self._load_generation = 0
        self._load_model()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="price-tag-parser",
            daemon=True,
        )
        self._worker.start()

    def _load_model(self) -> None:
        from price_tag_ai.config import AppConfig
        from price_tag_ai.train import PriceTagModel
        from price_tag_ai.train_hf import HFPriceTagModel

        checkpoint = torch.load(self._checkpoint_path, map_location=self._device)
        checkpoint_config = checkpoint.get("config", {})
        model_config = checkpoint_config.get("model", checkpoint_config)
        backbone = str(model_config.get("backbone", "resnet18"))
        dropout = float(model_config.get("dropout", 0.1))
        image_size = int(model_config.get("image_size", 224))
        trainer_type = str(checkpoint.get("trainer_type", "")).lower()
        state_dict = checkpoint["model_state_dict"]
        is_hf_checkpoint = (
            trainer_type == "hf"
            or any(key.startswith("encoder.embeddings.") or key.startswith("encoder.encoder.") for key in state_dict)
        )

        if is_hf_checkpoint:
            app_config = AppConfig.model_validate(checkpoint_config)
            model = HFPriceTagModel(
                config=app_config,
                binary_pos_weights={
                    "is_variable_weight": 1.0,
                    "is_ambiguous": 1.0,
                    "is_unparsable": 1.0,
                    "upc_present": 1.0,
                },
                load_pretrained_encoder=False,
            ).to(self._device)
            forward_image_key = "pixel_values"
            allow_compile = False
        else:
            model = PriceTagModel(
                backbone=backbone,
                dropout=dropout,
                pretrained=False,
            ).to(self._device)
            forward_image_key = "images"
            allow_compile = True
        model.load_state_dict(state_dict)
        model.eval()
        self._model = self._maybe_compile_model(model, allow_compile=allow_compile)
        self._forward_image_key = forward_image_key
        self._transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        self._checkpoint_mtime_ns = self._checkpoint_path.stat().st_mtime_ns
        self._load_generation += 1

    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        if not image_jpeg:
            raise ValueError("imageJpeg is required")
        task = _ParseTask(
            image_jpeg=image_jpeg,
            image_filename=image_filename,
            done=threading.Event(),
        )
        self._task_queue.put(task)
        task.done.wait()
        if task.error is not None:
            raise task.error
        assert task.result is not None
        return task.result

    def _worker_loop(self) -> None:
        while True:
            task = self._task_queue.get()
            if task is None:
                return
            try:
                self._reload_if_needed()
                task.result = self._parse_impl(task.image_jpeg, task.image_filename)
            except Exception as exc:
                task.error = exc
            finally:
                task.done.set()

    def _reload_if_needed(self) -> None:
        current_mtime_ns = self._checkpoint_path.stat().st_mtime_ns
        if self._checkpoint_mtime_ns == current_mtime_ns:
            return
        self._load_model()

    def _parse_impl(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        _ = image_filename
        assert self._transform is not None
        assert self._model is not None
        image = Image.open(io.BytesIO(image_jpeg)).convert("RGB")
        tensor = self._transform(image).unsqueeze(0).to(self._device)

        with torch.inference_mode():
            if self._forward_image_key == "pixel_values":
                outputs = self._model(pixel_values=tensor)
            else:
                outputs = self._model(tensor)

        unit_idx = int(outputs["unit_logits"].argmax(dim=1).item())
        unit = self._to_product_unit(self._units[unit_idx] if 0 <= unit_idx < len(self._units) else None)
        price_raw = float(outputs["price"].item())
        net_raw = float(outputs["net_quantity"].item())
        pack_raw = float(outputs["pack_count"].item())

        variable_weight = self._sigmoid_bool(outputs["variable_weight_logit"])
        ambiguous = self._sigmoid_bool(outputs["ambiguous_logit"])
        unparsable = self._sigmoid_bool(outputs["unparsable_logit"])
        upc_present = self._sigmoid_bool(outputs["upc_present_logit"])

        price_total = max(0.0, round(price_raw, 2))
        net_quantity = max(0.01, round(net_raw, 3))
        pack_count = None if variable_weight else max(1, int(round(pack_raw)))
        upc_parsable = False
        has_complete_pricing = (
            price_total is not None
            and net_quantity is not None
            and unit is not None
            and (pack_count is not None or variable_weight)
        )
        if has_complete_pricing:
            ambiguous = False
            unparsable = False
        message = None
        if unparsable:
            message = "The model could not reliably parse this image."
        elif ambiguous:
            message = "The model parsed this image with low confidence. Please verify fields."
        elif has_complete_pricing and not upc_parsable:
            message = "Pricing parsed. UPC was not parsed, so enter UPC manually or continue without UPC for variable-weight items."
        elif upc_present:
            message = "UPC appears present, but this model cannot decode UPC digits yet. Enter UPC manually."

        return ParsedPriceTag(
            ambiguous=ambiguous,
            unparsable=unparsable,
            upc_parsable=upc_parsable,
            upc=None,
            price_total=price_total,
            pack_count=pack_count,
            net_quantity=net_quantity,
            quantity_unit=unit,
            is_variable_weight=variable_weight,
            message=message,
        )

    def _sigmoid_bool(self, tensor: torch.Tensor) -> bool:
        value = torch.sigmoid(tensor).item()
        return bool(value >= 0.5)

    def _to_product_unit(self, raw: str | None) -> ProductUnit | None:
        if raw is None:
            return None
        normalized = raw.strip().upper()
        if normalized == "ITEM":
            normalized = "EA"
        try:
            return ProductUnit[normalized]
        except KeyError:
            return None

    def _maybe_compile_model(self, model: torch.nn.Module, allow_compile: bool) -> torch.nn.Module:
        if not allow_compile:
            return model
        compile_enabled = os.environ.get("GROCERY_AI_COMPILE", "1").strip().lower()
        if compile_enabled in {"0", "false", "no", "off"}:
            return model
        if self._device.type != "cuda":
            return model
        compile_fn = getattr(torch, "compile", None)
        if compile_fn is None:
            return model
        try:
            return compile_fn(model, mode="reduce-overhead")
        except Exception:
            return model


def create_default_price_tag_parser() -> PriceTagParser:
    try:
        checkpoint_path = resolve_checkpoint_path()
        return TorchCheckpointPriceTagParser(checkpoint_path)
    except Exception as exc:
        return FallbackPriceTagParser(f"Auto-parse unavailable on server: {exc}")


def resolve_checkpoint_path() -> Path:
    env_path = os.environ.get("GROCERY_AI_CHECKPOINT")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"GROCERY_AI_CHECKPOINT not found: {path}")

    outputs_dir = Path(__file__).resolve().parent.parent / "ai_server" / "outputs"
    if not outputs_dir.exists():
        raise FileNotFoundError(f"AI outputs directory not found: {outputs_dir}")

    candidates = sorted(
        outputs_dir.rglob("best*.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No checkpoint found. Set GROCERY_AI_CHECKPOINT.")
    return candidates[0]
