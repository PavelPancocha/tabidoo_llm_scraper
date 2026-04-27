from __future__ import annotations

import json
from typing import Any, Optional

from .constants import (
    CollectionDefaults,
    DefaultName,
    FieldType,
    Format,
    JsonDefaults,
    JsonKey,
    SanitizeDefaults,
    WorkflowStepType,
)
from .models import (
    ExtractedCode,
    ExtractedCodeFragment,
    ExtractedCustomScriptCodeFragment,
    ExtractedWorkflowCodeFragment,
)


class ScriptExtractor:
    _CALCULATED_TYPES = {
        str(FieldType.CALCULATED_CURRENT),
        str(FieldType.CALCULATED),
    }
    _BUTTON_TYPES = {
        str(FieldType.BUTTON_CURRENT),
        str(FieldType.BUTTON),
    }
    _FREE_HTML_TYPES = {
        str(FieldType.FREE_HTML_CURRENT),
        str(FieldType.FREE_HTML),
    }

    def extract(self, app_structure: dict[str, Any]) -> ExtractedCode:
        app_id = str(app_structure.get(JsonKey.ID, SanitizeDefaults.EMPTY))
        app_name = Format.APP_NAME.format(
            name=app_structure.get(JsonKey.NAME, SanitizeDefaults.EMPTY),
            internal=app_structure.get(JsonKey.INTERNAL_NAME, SanitizeDefaults.EMPTY),
        ).strip()
        fragments: list[ExtractedCodeFragment] = list(CollectionDefaults.EMPTY)

        tables = app_structure.get(JsonKey.TABLES)
        if not isinstance(tables, list):
            tables = CollectionDefaults.EMPTY

        for table in tables:
            if not isinstance(table, dict):
                continue
            table_name = str(table.get(JsonKey.INTERNAL_NAME_API, SanitizeDefaults.EMPTY)) or str(
                table.get(JsonKey.ID, SanitizeDefaults.EMPTY)
            )
            items = table.get(JsonKey.ITEMS)
            if not isinstance(items, list):
                items = CollectionDefaults.EMPTY

            for field in items:
                if not isinstance(field, dict):
                    continue
                field_type = str(field.get(JsonKey.TYPE, SanitizeDefaults.EMPTY))
                field_name = str(field.get(JsonKey.NAME, SanitizeDefaults.EMPTY))
                metadata = field.get(JsonKey.METADATA) if isinstance(field.get(JsonKey.METADATA), dict) else {}

                script_meta = metadata.get(JsonKey.SCRIPT) if isinstance(metadata.get(JsonKey.SCRIPT), dict) else {}
                freehtml_init_meta = (
                    metadata.get(JsonKey.FREE_HTML_INIT_SCRIPT)
                    if isinstance(metadata.get(JsonKey.FREE_HTML_INIT_SCRIPT), dict)
                    else {}
                )
                freehtml_content_meta = (
                    metadata.get(JsonKey.FREE_HTML_CONTENT)
                    if isinstance(metadata.get(JsonKey.FREE_HTML_CONTENT), dict)
                    else {}
                )

                if field_type in self._CALCULATED_TYPES or field_type in self._BUTTON_TYPES:
                    fragment = self._fragment_from_meta(table_name, field_name, script_meta)
                    if fragment:
                        fragments.append(fragment)

                if field_type in self._FREE_HTML_TYPES:
                    fragment = self._fragment_from_meta(table_name, field_name, freehtml_init_meta)
                    if fragment:
                        fragments.append(fragment)
                    html_fragment = self._fragment_from_html_meta(
                        table_name,
                        field_name,
                        freehtml_content_meta,
                    )
                    if html_fragment:
                        fragments.append(html_fragment)

            scripts = table.get(JsonKey.SCRIPTS)
            if isinstance(scripts, list):
                for script in scripts:
                    if not isinstance(script, dict):
                        continue
                    js = script.get(JsonKey.JS_SCRIPT)
                    ts = script.get(JsonKey.TS_SCRIPT)
                    if (
                        isinstance(js, str)
                        and js.strip()
                    ) or (
                        isinstance(ts, str)
                        and ts.strip()
                    ):
                        fragments.append(
                            ExtractedCodeFragment(
                                table=table_name,
                                field_name=str(script.get(JsonKey.NAME, DefaultName.TABLE_SCRIPT)),
                                code_js=js if isinstance(js, str) else SanitizeDefaults.EMPTY,
                                code_ts=ts if isinstance(ts, str) else SanitizeDefaults.EMPTY,
                            )
                        )

        return ExtractedCode(app_id=app_id, app_name=app_name, fragments=fragments)

    def _fragment_from_meta(
        self, table: str, field_name: str, meta: dict[str, Any]
    ) -> Optional[ExtractedCodeFragment]:
        js = meta.get(JsonKey.JS_SCRIPT)
        ts = meta.get(JsonKey.TS_SCRIPT)
        if (
            isinstance(js, str)
            and js.strip()
        ) or (
            isinstance(ts, str)
            and ts.strip()
        ):
            return ExtractedCodeFragment(
                table=table,
                field_name=field_name,
                code_js=js if isinstance(js, str) else SanitizeDefaults.EMPTY,
                code_ts=ts if isinstance(ts, str) else SanitizeDefaults.EMPTY,
            )
        return None

    def _fragment_from_html_meta(
        self, table: str, field_name: str, meta: dict[str, Any]
    ) -> Optional[ExtractedCodeFragment]:
        written_html = meta.get(JsonKey.WRITTEN_HTML)
        runable_html = meta.get(JsonKey.RUNABLE_HTML)
        html = written_html if isinstance(written_html, str) and written_html.strip() else runable_html
        if isinstance(html, str) and html.strip():
            return ExtractedCodeFragment(
                table=table,
                field_name=field_name,
                code_js=SanitizeDefaults.EMPTY,
                code_ts=SanitizeDefaults.EMPTY,
                code_html=html,
            )
        return None

    def extract_workflows(self, workflows: list[dict[str, Any]]) -> list[ExtractedWorkflowCodeFragment]:
        extracted: list[ExtractedWorkflowCodeFragment] = list(CollectionDefaults.EMPTY)
        for record in workflows:
            fields = record.get(JsonKey.FIELDS) if isinstance(record.get(JsonKey.FIELDS), dict) else {}
            name = str(fields.get(JsonKey.NAME, SanitizeDefaults.EMPTY))
            definition = fields.get(JsonKey.DEFINITION) if isinstance(fields.get(JsonKey.DEFINITION), dict) else {}
            triggers = definition.get(JsonKey.TRIGGERS)
            triggers_json = (
                json.dumps(triggers, ensure_ascii=True)
                if triggers is not None
                else JsonDefaults.EMPTY_ARRAY
            )
            steps = (
                definition.get(JsonKey.STEPS)
                if isinstance(definition.get(JsonKey.STEPS), list)
                else CollectionDefaults.EMPTY
            )
            extracted.extend(self._extract_workflow_steps(steps, name, triggers_json))
        return extracted

    def extract_custom_scripts(
        self, custom_scripts: list[dict[str, Any]]
    ) -> list[ExtractedCustomScriptCodeFragment]:
        extracted: list[ExtractedCustomScriptCodeFragment] = list(CollectionDefaults.EMPTY)
        for record in custom_scripts:
            fields = record.get(JsonKey.FIELDS) if isinstance(record.get(JsonKey.FIELDS), dict) else {}
            dts = fields.get(JsonKey.DTS) if isinstance(fields.get(JsonKey.DTS), dict) else {}
            script = fields.get(JsonKey.SCRIPT) if isinstance(fields.get(JsonKey.SCRIPT), dict) else {}
            extracted.append(
                ExtractedCustomScriptCodeFragment(
                    name=str(fields.get(JsonKey.NAME, SanitizeDefaults.EMPTY)),
                    namespace=str(fields.get(JsonKey.NAMESPACE, SanitizeDefaults.EMPTY)),
                    interface=str(fields.get(JsonKey.INTERFACE, SanitizeDefaults.EMPTY)),
                    dts=str(dts.get(JsonKey.RUNABLE_SCRIPT, SanitizeDefaults.EMPTY))
                    if dts.get(JsonKey.RUNABLE_SCRIPT) is not None
                    else SanitizeDefaults.EMPTY,
                    script=str(script.get(JsonKey.RUNABLE_SCRIPT, SanitizeDefaults.EMPTY))
                    if script.get(JsonKey.RUNABLE_SCRIPT) is not None
                    else SanitizeDefaults.EMPTY,
                )
            )
        return extracted

    def _extract_workflow_steps(
        self,
        steps: list[dict[str, Any]] | tuple[Any, ...],
        workflow_name: str,
        triggers_json: str,
    ) -> list[ExtractedWorkflowCodeFragment]:
        extracted: list[ExtractedWorkflowCodeFragment] = list(CollectionDefaults.EMPTY)
        for step in steps:
            if not isinstance(step, dict):
                continue

            data = step.get(JsonKey.DATA) if isinstance(step.get(JsonKey.DATA), dict) else {}
            if step.get(JsonKey.TYPE) == WorkflowStepType.JS_SCRIPT:
                script = data.get(JsonKey.SCRIPT) if isinstance(data.get(JsonKey.SCRIPT), dict) else {}
                code_js = (
                    script.get(JsonKey.RUNABLE_SCRIPT)
                    if isinstance(script.get(JsonKey.RUNABLE_SCRIPT), str)
                    else SanitizeDefaults.EMPTY
                )
                code_ts = (
                    script.get(JsonKey.WRITTEN_TYPESCRIPT)
                    if isinstance(script.get(JsonKey.WRITTEN_TYPESCRIPT), str)
                    else SanitizeDefaults.EMPTY
                )
                if code_js.strip() or code_ts.strip():
                    extracted.append(
                        ExtractedWorkflowCodeFragment(
                            workflow=workflow_name,
                            triggers=triggers_json,
                            code_js=code_js,
                            code_ts=code_ts,
                        )
                    )

            extracted.extend(self._extract_nested_workflow_definitions(data, workflow_name, triggers_json))

        return extracted

    def _extract_nested_workflow_definitions(
        self,
        value: Any,
        workflow_name: str,
        triggers_json: str,
    ) -> list[ExtractedWorkflowCodeFragment]:
        extracted: list[ExtractedWorkflowCodeFragment] = list(CollectionDefaults.EMPTY)

        if isinstance(value, dict):
            workflow_definition = value.get("workflowDefinition")
            if isinstance(workflow_definition, dict):
                nested_steps = workflow_definition.get(JsonKey.STEPS)
                if isinstance(nested_steps, list):
                    extracted.extend(self._extract_workflow_steps(nested_steps, workflow_name, triggers_json))

            for nested_value in value.values():
                if nested_value is not workflow_definition:
                    extracted.extend(
                        self._extract_nested_workflow_definitions(
                            nested_value,
                            workflow_name,
                            triggers_json,
                        )
                    )
        elif isinstance(value, list):
            for item in value:
                extracted.extend(self._extract_nested_workflow_definitions(item, workflow_name, triggers_json))

        return extracted
