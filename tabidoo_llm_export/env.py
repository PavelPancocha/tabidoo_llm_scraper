from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .constants import (
    Char,
    EnvDefaults,
    EnvVar,
    Encoding,
    JsonKey,
    RegexPattern,
    SanitizeDefaults,
    Text,
    UrlPart,
)
from .errors import InvalidConfigError

try:
    from dotenv import load_dotenv as dotenv_load
except ImportError:  # pragma: no cover - optional dependency
    dotenv_load = None


class EnvLoader:
    @staticmethod
    def load(path: Path) -> None:
        if dotenv_load is not None:
            dotenv_load(path, override=False)
            return
        if not path.exists():
            return
        content = path.read_text(encoding=Encoding.UTF8)
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(EnvDefaults.COMMENT) or EnvDefaults.ASSIGN not in line:
                continue
            key, value = line.split(EnvDefaults.ASSIGN, 1)
            key = key.strip()
            value = value.strip().strip(EnvDefaults.QUOTE_DOUBLE).strip(EnvDefaults.QUOTE_SINGLE)
            if key and key not in os.environ:
                os.environ[key] = value


class TokenProvider:
    @staticmethod
    def read() -> str:
        token = os.environ.get(EnvVar.API_TOKEN, SanitizeDefaults.EMPTY).strip()
        if token:
            return token
        raise InvalidConfigError(Text.MISSING_TOKEN)


class UrlNormalizer:
    @staticmethod
    def normalize(raw: str) -> str:
        value = raw.strip()
        if not value:
            raise InvalidConfigError(Text.EMPTY_BASE_URL)
        if not value.startswith(UrlPart.HTTP) and not value.startswith(UrlPart.HTTPS):
            raise InvalidConfigError(Text.BAD_BASE_URL)
        value = value.rstrip(Char.SLASH)
        if value.endswith(UrlPart.API_V2):
            return value[: -len(UrlPart.V2)]
        if value.endswith(UrlPart.API):
            return value
        return f"{value}{UrlPart.API}"


class JsonUnwrapper:
    @staticmethod
    def unwrap(payload: Any) -> Any:
        if isinstance(payload, dict) and JsonKey.DATA in payload:
            return payload[JsonKey.DATA]
        return payload


class Sanitizer:
    @staticmethod
    def sanitize(value: str) -> str:
        sanitized = value.strip().lower()
        sanitized = re.sub(RegexPattern.WHITESPACE, SanitizeDefaults.UNDERSCORE, sanitized)
        sanitized = re.sub(RegexPattern.INVALID, SanitizeDefaults.EMPTY, sanitized)
        sanitized = sanitized.strip(SanitizeDefaults.STRIP)
        return sanitized or SanitizeDefaults.FALLBACK

