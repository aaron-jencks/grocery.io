from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from openai import OpenAI
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
- quantity_unit: one of OZ, LB, EA, KG, G, LIT, ML, GAL, QT, PT
- pack_count: integer count of items in the package
- upc_present: true if a UPC/barcode number is visibly present in the image, else false
- upc_code: only the UPC digits if visible and readable, else null

Rules:
- Do not infer text product names.
- If a field is not clearly visible, return null for it.
- If the UPC is not clearly readable, set upc_present to false and upc_code to null.
- quantity_unit must match exactly one of the allowed values or be null.
- pack_count should be 1 when the tag clearly refers to a single item and no multipack is shown.
"""


class OpenAIPrefillService:
    def __init__(self, model: str | None = None, client: OpenAI | None = None):
        project_root = Path(__file__).resolve().parent.parent
        api_key = resolve_openai_api_key(project_root)
        self.model = model or resolve_openai_model(project_root) or "gpt-4.1"
        self.client = client or OpenAI(api_key=api_key)

    def extract(self, image_path: str | Path) -> PriceTagRecord:
        path = Path(image_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
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
        )
        parsed = response.output_parsed
        return PriceTagRecord(
            image_filename=path.name,
            price=parsed.price,
            net_quantity=parsed.net_quantity,
            quantity_unit=parsed.quantity_unit,
            pack_count=parsed.pack_count,
            upc_present=parsed.upc_present,
            upc_code=parsed.upc_code,
            prefilled_by_model=True,
        )
