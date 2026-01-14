from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import JsonKey, SanitizeDefaults


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class AppSummary:
    app_id: str
    name: str
    internal_name: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> AppSummary:
        return cls(
            app_id=str(payload.get(JsonKey.ID, SanitizeDefaults.EMPTY)),
            name=str(payload.get(JsonKey.NAME, SanitizeDefaults.EMPTY)),
            internal_name=str(payload.get(JsonKey.INTERNAL_NAME, SanitizeDefaults.EMPTY)),
        )


@dataclass(frozen=True)
class ExportStats:
    tables: int
    fields: int
    code_blocks: int
    workflows: int
    custom_scripts: int
    tsd_lines: int
    tsd_bytes: int
    llm_lines: int
    llm_bytes: int


@dataclass(frozen=True)
class ExtractedCodeFragment:
    table: str
    field_name: str
    code_js: str
    code_ts: str


@dataclass(frozen=True)
class ExtractedCode:
    app_id: str
    app_name: str
    fragments: list[ExtractedCodeFragment]


@dataclass(frozen=True)
class ExtractedWorkflowCodeFragment:
    workflow: str
    triggers: str
    code_js: str
    code_ts: str


@dataclass(frozen=True)
class ExtractedCustomScriptCodeFragment:
    name: str
    namespace: str
    interface: str
    dts: str
    script: str
