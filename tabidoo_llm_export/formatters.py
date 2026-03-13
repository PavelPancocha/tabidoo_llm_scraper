from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from typing import Optional

from .constants import JsonKey, MarkdownText, Newline, SanitizeDefaults, UiDefaults
from .models import (
    ExtractedCode,
    ExtractedCustomScriptCodeFragment,
    ExtractedWorkflowCodeFragment,
)


class LlmFormatter:
    def format(
        self,
        extracted: ExtractedCode,
        workflows: Optional[list[ExtractedWorkflowCodeFragment]],
        custom_scripts: Optional[list[ExtractedCustomScriptCodeFragment]],
    ) -> str:
        sections: list[str] = [
            f"{MarkdownText.TITLE_ANALYSIS}{Newline.DOUBLE}"
            f"{MarkdownText.APP_ID_LABEL.format(value=extracted.app_id)}{Newline.LF}"
            f"{MarkdownText.APP_NAME_LABEL.format(value=extracted.app_name)}{Newline.DOUBLE}"
        ]

        for idx, block in enumerate(extracted.fragments, start=UiDefaults.INDEX_START):
            sections.append(MarkdownText.BLOCK_PREFIX.format(index=idx) + Newline.LF)
            sections.append(MarkdownText.TABLE_LABEL.format(name=block.table))
            sections.append(MarkdownText.FIELD_LABEL.format(name=block.field_name) + Newline.LF)
            sections.extend(self._render_code_block(block.code_ts, block.code_js))

        if workflows:
            sections.append(f"{MarkdownText.TITLE_WORKFLOW}{Newline.DOUBLE}")
            for idx, wf in enumerate(workflows, start=UiDefaults.INDEX_START):
                sections.append(
                    MarkdownText.WORKFLOW_PREFIX.format(index=idx, name=wf.workflow) + Newline.LF
                )
                sections.append(MarkdownText.TRIGGERS_LABEL.format(value=wf.triggers) + Newline.LF)
                sections.extend(self._render_code_block(wf.code_ts, wf.code_js))

        if custom_scripts:
            sections.append(f"{MarkdownText.TITLE_CUSTOM}{Newline.DOUBLE}")
            for idx, cs in enumerate(custom_scripts, start=UiDefaults.INDEX_START):
                sections.append(
                    MarkdownText.CUSTOM_PREFIX.format(index=idx, name=cs.name) + Newline.LF
                )
                sections.append(MarkdownText.NAMESPACE_LABEL.format(value=cs.namespace) + Newline.LF)
                sections.append(MarkdownText.INTERFACE_LABEL.format(value=cs.interface) + Newline.LF)
                if cs.dts.strip():
                    sections.append(MarkdownText.DEFINITIONS_LABEL + Newline.LF)
                    sections.extend(self._render_code_block(cs.dts, SanitizeDefaults.EMPTY))
                sections.append(MarkdownText.SCRIPT_LABEL + Newline.LF)
                sections.extend(self._render_code_block(SanitizeDefaults.EMPTY, cs.script))

        return Newline.LF.join(sections)

    @staticmethod
    def _render_code_block(code_ts: str, code_js: str) -> list[str]:
        if code_ts.strip():
            return [
                f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}",
                code_ts,
                f"{MarkdownText.CODE_FENCE_END}{Newline.LF}",
            ]
        return [
            f"{MarkdownText.CODE_FENCE_JS}{Newline.LF}",
            code_js or SanitizeDefaults.EMPTY,
            f"{MarkdownText.CODE_FENCE_END}{Newline.LF}",
        ]


class TablesFormatter:
    def format(self, app_structure: dict[str, Any]) -> str:
        app_id = str(app_structure.get(JsonKey.ID, SanitizeDefaults.EMPTY))
        app_name = str(app_structure.get(JsonKey.NAME, SanitizeDefaults.EMPTY))
        app_internal = str(app_structure.get(JsonKey.INTERNAL_NAME, SanitizeDefaults.EMPTY))

        sections: list[str] = [
            f"{MarkdownText.TITLE_TABLES}{Newline.DOUBLE}"
            f"{MarkdownText.APP_ID_LABEL.format(value=app_id)}{Newline.LF}"
            f"{MarkdownText.APP_NAME_LABEL.format(value=app_name)}{Newline.LF}"
            f"{MarkdownText.APP_INTERNAL_LABEL.format(value=app_internal)}{Newline.DOUBLE}"
        ]

        tables = app_structure.get(JsonKey.TABLES) if isinstance(app_structure.get(JsonKey.TABLES), list) else []
        table_map = {
            str(table.get(JsonKey.ID, SanitizeDefaults.EMPTY)): table
            for table in tables
            if isinstance(table, dict)
        }
        rendered_table_ids: set[str] = set()

        modules = app_structure.get(JsonKey.MODULES)
        if isinstance(modules, list):
            for module in modules:
                if not isinstance(module, dict):
                    continue
                module_name = str(
                    module.get(JsonKey.HEADER)
                    or module.get(JsonKey.SHORT_ID)
                    or SanitizeDefaults.EMPTY
                ).strip()
                sections.append(
                    MarkdownText.MODULE_PREFIX.format(name=module_name or "Unnamed module")
                    + Newline.LF
                )
                table_ids = module.get(JsonKey.TABLE_IDS)
                for table in self._resolve_tables(table_ids, table_map):
                    table_id = str(table.get(JsonKey.ID, SanitizeDefaults.EMPTY))
                    rendered_table_ids.add(table_id)
                    sections.extend(self._render_table(table))

        ungrouped = [
            table
            for table in tables
            if isinstance(table, dict)
            and str(table.get(JsonKey.ID, SanitizeDefaults.EMPTY)) not in rendered_table_ids
        ]
        if ungrouped:
            sections.append(MarkdownText.UNGROUPED_TABLES + Newline.LF)
            for table in ungrouped:
                sections.extend(self._render_table(table))

        return Newline.LF.join(sections).rstrip() + Newline.LF

    def _resolve_tables(
        self,
        table_ids: Any,
        table_map: dict[str, dict[str, Any]],
    ) -> Iterable[dict[str, Any]]:
        if not isinstance(table_ids, list):
            return ()
        return [
            table_map[table_id]
            for table_id in table_ids
            if isinstance(table_id, str) and table_id in table_map
        ]

    def _render_table(self, table: dict[str, Any]) -> list[str]:
        table_header = str(
            table.get(JsonKey.HEADER)
            or table.get(JsonKey.INTERNAL_NAME_API)
            or table.get(JsonKey.ID, SanitizeDefaults.EMPTY)
        )
        table_internal = str(table.get(JsonKey.INTERNAL_NAME_API, SanitizeDefaults.EMPTY))
        table_id = str(table.get(JsonKey.ID, SanitizeDefaults.EMPTY))

        sections = [
            MarkdownText.TABLE_PREFIX.format(name=self._escape_cell(table_header)) + Newline.LF,
            MarkdownText.TABLE_INTERNAL_LABEL.format(value=table_internal),
            MarkdownText.TABLE_ID_LABEL.format(value=table_id) + Newline.LF,
            MarkdownText.TABLE_FIELDS_HEADER,
            MarkdownText.TABLE_FIELDS_SEPARATOR,
        ]

        items = table.get(JsonKey.ITEMS)
        if isinstance(items, list):
            for field in items:
                if not isinstance(field, dict):
                    continue
                metadata = field.get(JsonKey.METADATA) if isinstance(field.get(JsonKey.METADATA), dict) else {}
                required = metadata.get(JsonKey.REQUIRED)
                sections.append(
                    MarkdownText.TABLE_FIELD_ROW.format(
                        header=self._escape_cell(str(field.get(JsonKey.HEADER, SanitizeDefaults.EMPTY))),
                        name=self._escape_cell(str(field.get(JsonKey.NAME, SanitizeDefaults.EMPTY))),
                        type=self._escape_cell(str(field.get(JsonKey.TYPE, SanitizeDefaults.EMPTY))),
                        required="yes" if required is True else "no" if required is False else SanitizeDefaults.EMPTY,
                        description=self._escape_cell(
                            str(metadata.get(JsonKey.DESCRIPTION, SanitizeDefaults.EMPTY))
                        ),
                    )
                )

        sections.append(SanitizeDefaults.EMPTY)
        return sections

    @staticmethod
    def _escape_cell(value: str) -> str:
        return value.replace("|", "\\|").replace(Newline.LF, "<br>")


class MarkdownRenderer:
    @staticmethod
    def wrap_typescript(content: str) -> str:
        return (
            f"{MarkdownText.TITLE_TSD}{Newline.DOUBLE}"
            f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}"
            f"{content.rstrip()}{Newline.LF}{MarkdownText.CODE_FENCE_END}{Newline.LF}"
        )
