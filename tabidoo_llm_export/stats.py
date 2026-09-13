from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import CountDefaults, Encoding, JsonKey
from .models import (
    ExportStats,
    ExtractedCode,
    ExtractedCustomScriptCodeFragment,
    ExtractedWorkflowCodeFragment,
)


_LINE_BREAK = re.compile(r"\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]")


class StatsBuilder:
    @staticmethod
    def build(
        app_full: dict[str, Any],
        extracted: ExtractedCode,
        workflows: list[ExtractedWorkflowCodeFragment],
        custom_scripts: list[ExtractedCustomScriptCodeFragment],
        schema_md: Path | None,
        tables_md: str,
        llm: str,
    ) -> ExportStats:
        tables = app_full.get(JsonKey.TABLES)
        table_count = len(tables) if isinstance(tables, list) else CountDefaults.ZERO
        field_count = CountDefaults.ZERO
        if isinstance(tables, list):
            for table in tables:
                if isinstance(table, dict) and isinstance(table.get(JsonKey.ITEMS), list):
                    field_count += len(table.get(JsonKey.ITEMS))
        schema_lines = 0
        last_character = ""
        if schema_md is not None:
            with schema_md.open("r", encoding=Encoding.UTF8, newline="") as source:
                for chunk in iter(lambda: source.read(65_536), ""):
                    schema_lines += sum(1 for _ in _LINE_BREAK.finditer(chunk))
                    if last_character == "\r" and chunk.startswith("\n"):
                        schema_lines -= 1
                    last_character = chunk[-1]
            if last_character and not _LINE_BREAK.fullmatch(last_character):
                schema_lines += 1
        return ExportStats(
            tables=table_count,
            fields=field_count,
            code_blocks=len(extracted.fragments),
            workflows=len(workflows),
            custom_scripts=len(custom_scripts),
            schema_lines=schema_lines,
            schema_bytes=schema_md.stat().st_size if schema_md is not None else 0,
            tables_md_lines=len(tables_md.splitlines()),
            tables_md_bytes=len(tables_md.encode(Encoding.UTF8)),
            llm_lines=len(llm.splitlines()),
            llm_bytes=len(llm.encode(Encoding.UTF8)),
        )
