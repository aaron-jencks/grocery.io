from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import os
import io

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
        project_root = Path(__file__).resolve().parent.parent
        ai_root = project_root / "ai_server"
        import sys
        if str(ai_root) not in sys.path:
            sys.path.insert(0, str(ai_root))
        from price_tag_ai.train import PriceTagModel, UNITS

        self._units: list[str] = list(UNITS)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        checkpoint = torch.load(checkpoint_path, map_location=self._device)
        model_config = checkpoint.get("config", {}).get("model", checkpoint.get("config", {}))
        backbone = str(model_config.get("backbone", "resnet18"))
        dropout = float(model_config.get("dropout", 0.1))
        image_size = int(model_config.get("image_size", 224))
        self._model = PriceTagModel(
            backbone=backbone,
            dropout=dropout,
            pretrained=False,
        ).to(self._device)
        self._model.load_state_dict(checkpoint["model_state_dict"])
        self._model.eval()
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

    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        if not image_jpeg:
            raise ValueError("imageJpeg is required")
        _ = image_filename
        image = Image.open(io.BytesIO(image_jpeg)).convert("RGB")
        tensor = self._transform(image).unsqueeze(0).to(self._device)

        with torch.no_grad():
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
        message = None
        if unparsable:
            message = "The model could not reliably parse this image."
        elif ambiguous:
            message = "The model parsed this image with low confidence. Please verify fields."
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
