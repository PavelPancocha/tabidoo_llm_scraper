from __future__ import annotations

import json
import textwrap
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from rich.console import Console

from .constants import (
    Attr,
    BytesDefaults,
    Char,
    CollectionDefaults,
    DecodeDefaults,
    Defaults,
    Encoding,
    ErrorKey,
    ExitCode,
    Format,
    HeaderName,
    HeaderValue,
    HttpMethod,
    HttpStatus,
    Limits,
    Separator,
    Style,
    Text,
    TextDefaults,
)
from .errors import ApiError, AuthError, HttpStatusError, NetworkError
from .models import HttpResponse


class HttpErrorFormatter:
    @staticmethod
    def format(status: int, url: str, body: bytes) -> str:
        text = body.decode(Encoding.UTF8, errors=DecodeDefaults.ERROR_HANDLER).strip()
        if not text:
            return Text.HTTP_EMPTY.format(status=status, url=url)
        try:
            payload = json.loads(text)
            if (
                isinstance(payload, dict)
                and ErrorKey.ERRORS in payload
                and isinstance(payload[ErrorKey.ERRORS], list)
            ):
                messages: list[str] = list(CollectionDefaults.EMPTY)
                for item in payload[ErrorKey.ERRORS]:
                    if isinstance(item, dict) and ErrorKey.MESSAGE in item:
                        messages.append(str(item[ErrorKey.MESSAGE]))
                if messages:
                    return Text.HTTP_ERROR.format(
                        status=status, url=url, message=Separator.ERROR_JOIN.join(messages)
                    )
        except Exception:
            pass
        trimmed = textwrap.shorten(text, width=Limits.ERROR_BODY_WIDTH, placeholder=TextDefaults.ELLIPSIS)
        return Text.HTTP_ERROR.format(status=status, url=url, message=trimmed)


class HttpClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        language: str,
        timeout_sec: int,
        verbose: bool,
        console: Console,
    ) -> None:
        self._base_url = base_url
        self._token = token
        self._language = language
        self._timeout_sec = timeout_sec
        self._verbose = verbose
        self._console = console

    def _build_url(self, path: str) -> str:
        return urljoin(
            self._base_url.rstrip(Char.SLASH) + Char.SLASH,
            path.lstrip(Char.SLASH),
        )

    def _default_headers(self) -> dict[str, str]:
        accept_language = Format.ACCEPT_LANGUAGE.format(
            language=self._language,
            quality=Defaults.ACCEPT_LANGUAGE_QUALITY,
        )
        return {
            HeaderName.AUTHORIZATION: f"{HeaderValue.AUTH_SCHEME} {self._token}",
            HeaderName.ACCEPT: HeaderValue.ACCEPT_FE,
            HeaderName.ACCEPT_LANGUAGE: accept_language,
            HeaderName.USER_AGENT: HeaderValue.USER_AGENT,
        }

    def request(
        self,
        method: HttpMethod,
        path: str,
        json_body: Any | None,
        extra_headers: Optional[dict[str, str]],
    ) -> HttpResponse:
        url = self._build_url(path)
        headers = self._default_headers()
        if json_body is not None:
            headers[HeaderName.CONTENT_TYPE] = HeaderValue.CONTENT_JSON
        if extra_headers:
            headers.update(extra_headers)

        data: Optional[bytes] = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=True).encode(Encoding.UTF8)

        if self._verbose:
            self._console.print(f"{method} {url}", style=Style.INFO)

        request = Request(url=url, method=method, headers=headers, data=data)
        try:
            with urlopen(request, timeout=self._timeout_sec) as resp:
                body = resp.read()
                return HttpResponse(
                    status=getattr(resp, Attr.STATUS, int(ExitCode.SUCCESS)),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    body=body,
                )
        except HTTPError as exc:
            body = exc.read() if exc.fp else BytesDefaults.EMPTY
            status = exc.code
            message = HttpErrorFormatter.format(status, url, body)
            if status in (HttpStatus.UNAUTHORIZED, HttpStatus.FORBIDDEN):
                raise AuthError(message) from exc
            raise HttpStatusError(status, message) from exc
        except URLError as exc:
            raise NetworkError(Text.NETWORK_ERROR.format(url=url, detail=exc)) from exc

    def get_json(self, path: str, headers: Optional[dict[str, str]] = None) -> Any:
        resp = self.request(HttpMethod.GET, path, None, headers)
        try:
            return json.loads(resp.body.decode(Encoding.UTF8))
        except Exception as exc:
            raise ApiError(Text.JSON_ERROR_GET.format(path=path)) from exc

    def post_json(self, path: str, body: Any, headers: Optional[dict[str, str]] = None) -> Any:
        resp = self.request(HttpMethod.POST, path, body, headers)
        try:
            return json.loads(resp.body.decode(Encoding.UTF8))
        except Exception as exc:
            raise ApiError(Text.JSON_ERROR_POST.format(path=path)) from exc
