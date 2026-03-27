from __future__ import annotations

import base64
import io
import time
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from price_tag_ai.dataset import PriceTagRecord
from price_tag_ai.local_config import resolve_openai_api_key, resolve_openai_model


class PriceTagPrefill(BaseModel):
    price: float | None = Field(default=None)
    net_quantity: float | None = Field(default=None)
    quantity_unit: str | None = Field(default=None)
    pack_count: int | None = Field(default=None)
    upc_present: bool = Field(default=False)
    upc_code: str | None = Field(default=None)


PROMPT = """You extract structured numeric data from grocery store shelf price tag photos.

Return only the following fields when visible:
- price: the displayed total price as a decimal number
- net_quantity: the size of each item, as a decimal number
- quantity_unit: one of OZ, LB, ITEM, KG, G, LIT, ML, GAL, QT, PT, TSP, TBSP, FL_OZ, CUP
- pack_count: integer count of items in the package
- upc_present: true if a UPC/barcode number is visibly present in the image, else false
- upc_code: only the UPC digits if visible and readable, else null

Rules:
- Do not infer text product names.
- If a field is not clearly visible, return null for it.
- If the UPC is not clearly readable, set upc_present to false and upc_code to null.
- quantity_unit must match exactly one of the allowed values or be null. Prefer ITEM over EA.
- pack_count should be 1 when the tag clearly refers to a single item and no multipack is shown.
"""

MAX_IMAGE_DIMENSION = 1024
JPEG_QUALITY = 75
OPENAI_REQUEST_TIMEOUT_SECONDS = 20


class OpenAIPrefillService:
    def __init__(self, model: str | None = None, client: OpenAI | None = None):
        project_root = Path(__file__).resolve().parent.parent
        api_key = resolve_openai_api_key(project_root)
        self.model = model or resolve_openai_model(project_root) or "gpt-4.1"
        self.client = client or OpenAI(api_key=api_key)

    def smoke_test(self) -> None:
        print("[openai] smoke test: starting", flush=True)
        try:
            self.client.models.list(timeout=10)
            print("[openai] smoke test: success", flush=True)
        except Exception as exc:
            print(f"[openai] smoke test: failed: {exc}", flush=True)
            raise RuntimeError(
                f"OpenAI smoke test failed: {exc}"
            ) from exc

    def extract(self, image_path: str | Path) -> PriceTagRecord:
        path = Path(image_path)
        started = time.perf_counter()
        print(f"[prefill] {path.name}: preparing image", flush=True)
        mime_type, image_b64 = self._encode_image_for_model(path)
        print(
            f"[prefill] {path.name}: encoded for upload (base64 bytes={len(image_b64)})",
            flush=True,
        )
        try:
            print(
                f"[prefill] {path.name}: sending request to OpenAI model={self.model}",
                flush=True,
            )
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": PROMPT,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Extract the numeric price tag fields from this image.",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_b64}",
                            },
                        ],
                    },
                ],
                text_format=PriceTagPrefill,
                timeout=OPENAI_REQUEST_TIMEOUT_SECONDS,
            )
            print(f"[prefill] {path.name}: OpenAI response received", flush=True)
        except Exception as exc:
            print(f"[prefill] {path.name}: request failed: {exc}", flush=True)
            raise RuntimeError(f"OpenAI prefill request failed: {exc}") from exc
        parsed = response.output_parsed
        elapsed = time.perf_counter() - started
        print(f"[prefill] {path.name}: parsed output in {elapsed:.2f}s", flush=True)
        quantity_unit = self._normalize_quantity_unit(parsed.quantity_unit)
        return PriceTagRecord(
            image_filename=path.name,
            price=parsed.price,
            net_quantity=parsed.net_quantity,
            quantity_unit=quantity_unit,
            pack_count=parsed.pack_count,
            upc_present=parsed.upc_present,
            upc_code=parsed.upc_code,
            prefilled_by_model=True,
        )

    def _encode_image_for_model(self, image_path: Path) -> tuple[str, str]:
        print(f"[prefill] {image_path.name}: loading image bytes", flush=True)
        with Image.open(image_path) as image:
            normalized = ImageOps.exif_transpose(image)
            rgb = normalized.convert("RGB")
            rgb.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return "image/jpeg", image_b64

    def _normalize_quantity_unit(self, unit: str | None) -> str | None:
        if unit is None:
            return None
        normalized = unit.strip().upper()
        if normalized == "EA":
            return "ITEM"
        return normalized
