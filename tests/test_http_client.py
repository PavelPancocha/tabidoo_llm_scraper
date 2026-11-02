from __future__ import annotations

import io
import socket
import unittest
from email.message import Message
from http.client import RemoteDisconnected
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from rich.console import Console

from tabidoo_llm_export.constants import HttpMethod
from tabidoo_llm_export.errors import AuthError, HttpStatusError, NetworkError
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

    def test_get_retries_transport_failures_with_four_attempts(self) -> None:
        for error_type in (URLError, TimeoutError, socket.timeout, ConnectionResetError, RemoteDisconnected):
            for succeeds in (True, False):
                with self.subTest(error=error_type.__name__, succeeds=succeeds):
                    error = error_type("offline")
                    outcomes = [error] * 3 + [Response()] if succeeds else [error] * 4
                    with patch("tabidoo_llm_export.http_client.urlopen", side_effect=outcomes) as opened, patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
                        if succeeds:
                            response = self.client().request(HttpMethod.GET, "/v2/apps", None, None)
                            self.assertEqual(response.body, b'{"ok":true}')
                        else:
                            with self.assertRaises(NetworkError) as caught:
                                self.client().request(HttpMethod.GET, "/v2/apps", None, None)
                            self.assertIs(caught.exception.__cause__, error)
                    self.assertEqual(opened.call_count, 4)
                    self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0, 1.5])

    def test_post_never_retries_transport_failures(self) -> None:
        for error_type in (URLError, TimeoutError, socket.timeout, ConnectionResetError, RemoteDisconnected):
            for body_failure in (False, True):
                with self.subTest(error=error_type.__name__, body_failure=body_failure):
                    error = error_type("offline")
                    with patch("tabidoo_llm_export.http_client.urlopen", side_effect=[Response() if body_failure else error]) as opened, patch.object(Response, "read", side_effect=error), patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
                        with self.assertRaises(NetworkError):
                            self.client().request(HttpMethod.POST, "/v2/apps/getApplicationTypeScriptDefinition", {}, None)
                    self.assertEqual(opened.call_count, 1)
                    sleep.assert_not_called()

    def test_get_retries_body_transport_failures(self) -> None:
        for error_type in (TimeoutError, socket.timeout, ConnectionResetError, RemoteDisconnected):
            with self.subTest(error=error_type.__name__):
                with patch("tabidoo_llm_export.http_client.urlopen", side_effect=[Response(), Response()]) as opened, patch.object(Response, "read", side_effect=[error_type("offline"), b"ok"]), patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
                    response = self.client().request(HttpMethod.GET, "/v2/apps", None, None)
                self.assertEqual(response.body, b"ok")
                self.assertEqual(opened.call_count, 2)
                sleep.assert_called_once_with(0.5)

    def test_http_status_errors_are_never_retried(self) -> None:
        for status in (401, 403, 429, 500, 503):
            with self.subTest(status=status):
                error = HTTPError("offline", status, "offline", {}, io.BytesIO(b"failure"))
                with patch("tabidoo_llm_export.http_client.urlopen", side_effect=error) as opened, patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
                    with self.assertRaises(AuthError if status in (401, 403) else HttpStatusError) as caught:
                        self.client().request(HttpMethod.GET, "/v2/apps", None, None)
                if status not in (401, 403):
                    self.assertEqual(caught.exception.status, status)
                opened.assert_called_once()
                sleep.assert_not_called()

    def test_unrelated_failure_is_not_retried(self) -> None:
        with patch("tabidoo_llm_export.http_client.urlopen", side_effect=ValueError("invalid")) as opened, patch("tabidoo_llm_export.http_client.time.sleep") as sleep:
            with self.assertRaises(ValueError):
                self.client().request(HttpMethod.GET, "/v2/apps", None, None)
        opened.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
