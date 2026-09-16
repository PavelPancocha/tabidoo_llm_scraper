from __future__ import annotations

import io
import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import URLError

from rich.console import Console

from tabidoo_llm_export.constants import HttpMethod
from tabidoo_llm_export.errors import NetworkError
from tabidoo_llm_export.http_client import HttpClient


class Response:
    status = 200
    headers = Message()

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    @staticmethod
    def read() -> bytes:
        return b'{"ok":true}'


class HttpClientTests(unittest.TestCase):
    def client(self) -> HttpClient:
        return HttpClient("https://example.invalid/api", "test", "en", 10, False, Console(file=io.StringIO()))

    def test_retries_transport_failures_only_with_a_fixed_bound(self) -> None:
        with patch("tabidoo_llm_export.http_client.urlopen", side_effect=[URLError("eof"), URLError("eof"), Response()]) as urlopen_mock, patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
            response = self.client().request(HttpMethod.GET, "/v2/apps", None, None)
        self.assertEqual(response.body, b'{"ok":true}')
        self.assertEqual(urlopen_mock.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0])

        with patch("tabidoo_llm_export.http_client.urlopen", side_effect=URLError("eof")) as urlopen_mock, patch("tabidoo_llm_export.http_client.time.sleep") as sleep, self.assertRaises(NetworkError):
            self.client().request(HttpMethod.POST, "/v2/apps/getApplicationTypeScriptDefinition", {}, None)
        self.assertEqual(urlopen_mock.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
