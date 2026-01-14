from __future__ import annotations

from typing import Any

from .constants import CountDefaults, Encoding, JsonKey
from .models import (
    ExportStats,
    ExtractedCode,
    ExtractedCustomScriptCodeFragment,
    ExtractedWorkflowCodeFragment,
)


class StatsBuilder:
    @staticmethod
    def build(
        app_full: dict[str, Any],
        extracted: ExtractedCode,
        workflows: list[ExtractedWorkflowCodeFragment],
        custom_scripts: list[ExtractedCustomScriptCodeFragment],
        tsd: str,
        llm: str,
    ) -> ExportStats:
        tables = app_full.get(JsonKey.TABLES)
        table_count = len(tables) if isinstance(tables, list) else CountDefaults.ZERO
        field_count = CountDefaults.ZERO
        if isinstance(tables, list):
            for table in tables:
                if isinstance(table, dict) and isinstance(table.get(JsonKey.ITEMS), list):
                    field_count += len(table.get(JsonKey.ITEMS))
        return ExportStats(
            tables=table_count,
            fields=field_count,
            code_blocks=len(extracted.fragments),
            workflows=len(workflows),
            custom_scripts=len(custom_scripts),
            tsd_lines=len(tsd.splitlines()),
            tsd_bytes=len(tsd.encode(Encoding.UTF8)),
            llm_lines=len(llm.splitlines()),
            llm_bytes=len(llm.encode(Encoding.UTF8)),
        )
