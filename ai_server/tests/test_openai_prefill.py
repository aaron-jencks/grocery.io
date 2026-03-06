from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from price_tag_ai.openai_prefill import OPENAI_REQUEST_TIMEOUT_SECONDS, OpenAIPrefillService


class _FakeModelsClientOk:
    def list(self, timeout: int) -> list[str]:
        return ["ok"]


class _FakeModelsClientFail:
    def list(self, timeout: int) -> list[str]:
        raise ValueError("boom")


class _FakeOpenAIClient:
    def __init__(self, models, responses=None):
        self.models = models
        self.responses = responses


class _ParsedPayload:
    price = 4.99
    net_quantity = 12.0
    quantity_unit = "OZ"
    pack_count = 1
    upc_present = False
    upc_code = None


class _FakeParseResponse:
    output_parsed = _ParsedPayload()


class _FakeResponsesClientOk:
    def __init__(self):
        self.timeout_seen = None

    def parse(self, **kwargs):
        self.timeout_seen = kwargs.get("timeout")
        return _FakeParseResponse()


class OpenAIPrefillSmokeTest(unittest.TestCase):
    def test_smoke_test_succeeds(self) -> None:
        service = OpenAIPrefillService(
            client=_FakeOpenAIClient(_FakeModelsClientOk()),
        )

        service.smoke_test()

    def test_smoke_test_raises_runtime_error_on_failure(self) -> None:
        service = OpenAIPrefillService(
            client=_FakeOpenAIClient(_FakeModelsClientFail()),
        )

        with self.assertRaises(RuntimeError) as raised:
            service.smoke_test()

        self.assertIn("OpenAI smoke test failed", str(raised.exception))

    def test_extract_uses_timeout_and_returns_record(self) -> None:
        fake_responses = _FakeResponsesClientOk()
        service = OpenAIPrefillService(
            client=_FakeOpenAIClient(_FakeModelsClientOk(), fake_responses),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.jpg"
            Image.new("RGB", (640, 480), "white").save(image_path)

            record = service.extract(image_path)

        self.assertEqual(OPENAI_REQUEST_TIMEOUT_SECONDS, fake_responses.timeout_seen)
        self.assertEqual("sample.jpg", record.image_filename)
        self.assertEqual(4.99, record.price)
