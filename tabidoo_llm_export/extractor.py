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
    MarkdownText,
    Newline,
    SanitizeDefaults,
    Separator,
    UiDefaults,
    WidgetType,
    WorkflowStepType,
)
from .models import (
    ExtractedCode,
    ExtractedCodeFragment,
    ExtractedCustomScriptCodeFragment,
    ExtractedWidgetCodeFragment,
    ExtractedWorkflowCodeFragment,
)
from .errors import ApiError


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
            emitted_table_script_names: set[str] = set()
            if isinstance(scripts, list):
                for script in scripts:
                    if not isinstance(script, dict):
                        continue
                    fragment = self._fragment_from_table_script(table_name, script)
                    if fragment:
                        fragments.append(fragment)
                        emitted_table_script_names.add(fragment.field_name)

            json_part = self._parse_json_part(table.get(JsonKey.JSON_PART))
            json_part_scripts = json_part.get(JsonKey.JS_SCRIPTS)
            if isinstance(json_part_scripts, list):
                for script in json_part_scripts:
                    if not isinstance(script, dict):
                        continue
                    fragment = self._fragment_from_tabidoo_code_object(
                        table_name,
                        str(script.get(JsonKey.NAME, DefaultName.TABLE_SCRIPT)),
                        script,
                    )
                    if fragment and fragment.field_name not in emitted_table_script_names:
                        fragments.append(fragment)

            form_logic_definitions = table.get(JsonKey.FORM_LOGIC_DEFINITIONS)
            if not isinstance(form_logic_definitions, list):
                form_logic_definitions = json_part.get(JsonKey.FORM_LOGIC_DEFINITIONS)
            if isinstance(form_logic_definitions, list):
                fragments.extend(self._extract_form_logic_definition_scripts(table_name, form_logic_definitions))

        return ExtractedCode(app_id=app_id, app_name=app_name, fragments=fragments)

    def _fragment_from_table_script(
        self,
        table_name: str,
        script: dict[str, Any],
    ) -> Optional[ExtractedCodeFragment]:
        return self._fragment_from_script_pair(
            table_name,
            str(script.get(JsonKey.NAME, DefaultName.TABLE_SCRIPT)),
            script.get(JsonKey.JS_SCRIPT),
            script.get(JsonKey.TS_SCRIPT),
        )

    def _parse_json_part(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _extract_form_logic_definition_scripts(
        self,
        table_name: str,
        definitions: list[Any],
    ) -> list[ExtractedCodeFragment]:
        fragments: list[ExtractedCodeFragment] = list(CollectionDefaults.EMPTY)
        for definition in definitions:
            if not isinstance(definition, dict):
                continue
            event_type = str(definition.get(JsonKey.TYPE, SanitizeDefaults.EMPTY)) or "formLogic"
            items = definition.get(JsonKey.ITEMS)
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items, start=UiDefaults.INDEX_START):
                if not isinstance(item, dict):
                    continue
                script = item.get(JsonKey.SCRIPT) if isinstance(item.get(JsonKey.SCRIPT), dict) else {}
                title = str(item.get(JsonKey.TITLE, SanitizeDefaults.EMPTY)).strip()
                script_name = str(script.get(JsonKey.NAME, DefaultName.TABLE_SCRIPT)).strip()
                label_parts = [
                    "formLogicDefinitions",
                    event_type,
                    title or f"step {index}",
                    script_name or DefaultName.TABLE_SCRIPT,
                ]
                fragment = self._fragment_from_tabidoo_code_object(
                    table_name,
                    " / ".join(label_parts),
                    script,
                )
                if fragment:
                    fragments.append(fragment)
        return fragments

    def _fragment_from_tabidoo_code_object(
        self,
        table_name: str,
        field_name: str,
        script: dict[str, Any],
    ) -> Optional[ExtractedCodeFragment]:
        return self._fragment_from_script_pair(
            table_name,
            field_name,
            script.get(JsonKey.RUNABLE_SCRIPT),
            script.get(JsonKey.WRITTEN_TYPESCRIPT),
        )

    def _fragment_from_script_pair(
        self,
        table_name: str,
        field_name: str,
        js: Any,
        ts: Any,
    ) -> Optional[ExtractedCodeFragment]:
        if (
            isinstance(js, str)
            and js.strip()
        ) or (
            isinstance(ts, str)
            and ts.strip()
        ):
            return ExtractedCodeFragment(
                table=table_name,
                field_name=field_name,
                code_js=js if isinstance(js, str) else SanitizeDefaults.EMPTY,
                code_ts=ts if isinstance(ts, str) else SanitizeDefaults.EMPTY,
            )
        return None

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
            fields = record.get(JsonKey.FIELDS)
            # Legacy never-configured workflows come back without a `definition` key at all,
            # but with their name; they hold no code. Any other missing/partial shape still fails.
            if isinstance(fields, dict) and JsonKey.DEFINITION not in fields and isinstance(fields.get(JsonKey.NAME), str) and fields.get(JsonKey.NAME):
                continue
            if not isinstance(fields, dict) or not isinstance(fields.get(JsonKey.DEFINITION), dict):
                raise ApiError("Incomplete workflow fields/definition")
            name = str(fields.get(JsonKey.NAME, SanitizeDefaults.EMPTY))
            definition = fields[JsonKey.DEFINITION]
            if not isinstance(definition.get(JsonKey.TRIGGERS), list) or not isinstance(definition.get(JsonKey.STEPS), list):
                raise ApiError("Incomplete workflow triggers/steps")
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
            fields = record.get(JsonKey.FIELDS)
            if not isinstance(fields, dict) or not isinstance(fields.get(JsonKey.SCRIPT), dict):
                raise ApiError("Incomplete custom script fields/script")
            script_value = fields[JsonKey.SCRIPT]
            if JsonKey.RUNABLE_SCRIPT not in script_value or script_value[JsonKey.RUNABLE_SCRIPT] is not None and not isinstance(script_value[JsonKey.RUNABLE_SCRIPT], str):
                raise ApiError("Incomplete custom script content")
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

    def extract_widgets(self, widgets: list[dict[str, Any]]) -> list[ExtractedWidgetCodeFragment]:
        """Dashboard widgets with markup or code, sorted by widget ID so repeated exports diff cleanly."""
        extracted: list[ExtractedWidgetCodeFragment] = list(CollectionDefaults.EMPTY)
        for record in widgets:
            fields = record.get(JsonKey.FIELDS)
            if not isinstance(fields, dict) or not isinstance(fields.get(JsonKey.DEFINITIONS), dict):
                raise ApiError("Incomplete widget fields/definitions")
            definitions = (
                fields.get(JsonKey.DEFINITIONS) if isinstance(fields.get(JsonKey.DEFINITIONS), dict) else {}
            )
            if not isinstance(definitions.get(JsonKey.SETTINGS), dict) or not isinstance(definitions.get(JsonKey.ID_WIDGET_TYPE), str) or not definitions[JsonKey.ID_WIDGET_TYPE].strip():
                raise ApiError("Incomplete widget type/settings")
            settings = (
                definitions.get(JsonKey.SETTINGS) if isinstance(definitions.get(JsonKey.SETTINGS), dict) else {}
            )
            widget_type = str(definitions.get(JsonKey.ID_WIDGET_TYPE) or SanitizeDefaults.EMPTY)
            if widget_type == WidgetType.TEXT and not isinstance(settings.get(JsonKey.TEXT_I18N), dict):
                raise ApiError("Incomplete text widget content")
            if widget_type == WidgetType.FREE_HTML and not isinstance(settings.get(JsonKey.FREE_HTML_CONTENT), dict) and not isinstance(settings.get(JsonKey.FREE_HTML_INIT_SCRIPT), dict):
                raise ApiError("Incomplete HTML widget content")
            script = (
                settings.get(JsonKey.FREE_HTML_INIT_SCRIPT)
                if isinstance(settings.get(JsonKey.FREE_HTML_INIT_SCRIPT), dict)
                else {}
            )
            code_ts = self._text(script.get(JsonKey.WRITTEN_TYPESCRIPT))
            code_js = self._text(script.get(JsonKey.RUNABLE_SCRIPT))
            html = (
                self._localized_html(settings.get(JsonKey.TEXT_I18N))
                if widget_type == WidgetType.TEXT
                else self._widget_html(settings.get(JsonKey.FREE_HTML_CONTENT))
            )
            if not (html.strip() or code_ts.strip() or code_js.strip()):
                continue
            version = record.get(JsonKey.VER)
            extracted.append(
                ExtractedWidgetCodeFragment(
                    widget_id=str(record.get(JsonKey.ID) or SanitizeDefaults.EMPTY),
                    widget_type=widget_type,
                    version=SanitizeDefaults.EMPTY if version is None else str(version),
                    header=self._localized_header(settings.get(JsonKey.HEADERS_I18N)),
                    html=html,
                    code_ts=code_ts,
                    code_js=code_js,
                )
            )
        return sorted(extracted, key=lambda widget: widget.widget_id)

    @staticmethod
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else SanitizeDefaults.EMPTY

    @classmethod
    def _widget_html(cls, content: Any) -> str:
        if not isinstance(content, dict):
            return SanitizeDefaults.EMPTY
        written = cls._text(content.get(JsonKey.WRITTEN_HTML))
        return written if written.strip() else cls._text(content.get(JsonKey.RUNABLE_HTML))

    @classmethod
    def _localized_html(cls, texts: Any) -> str:
        if not isinstance(texts, dict):
            return SanitizeDefaults.EMPTY
        entries = [(str(language), cls._text(text)) for language, text in sorted(texts.items()) if cls._text(text).strip()]
        if len(entries) == 1:
            return entries[0][1]
        return Newline.LF.join(
            MarkdownText.WIDGET_LANGUAGE_COMMENT.format(language=language) + Newline.LF + text
            for language, text in entries
        )

    @classmethod
    def _localized_header(cls, headers: Any) -> str:
        if not isinstance(headers, dict):
            return SanitizeDefaults.EMPTY
        values = [cls._text(text).strip() for _, text in sorted(headers.items())]
        return Separator.LANGUAGE_VARIANTS.join(dict.fromkeys(value for value in values if value))

    def _extract_workflow_steps(
        self,
        steps: list[dict[str, Any]] | tuple[Any, ...],
        workflow_name: str,
        triggers_json: str,
    ) -> list[ExtractedWorkflowCodeFragment]:
        extracted: list[ExtractedWorkflowCodeFragment] = list(CollectionDefaults.EMPTY)
        for step in steps:
            if not isinstance(step, dict):
                raise ApiError("Invalid workflow step")

            data = step.get(JsonKey.DATA) if isinstance(step.get(JsonKey.DATA), dict) else {}
            if step.get(JsonKey.TYPE) == WorkflowStepType.JS_SCRIPT:
                if not isinstance(data.get(JsonKey.SCRIPT), dict):
                    raise ApiError("Incomplete workflow script step")
                script = data[JsonKey.SCRIPT]
                if not any(key in script for key in (JsonKey.RUNABLE_SCRIPT, JsonKey.WRITTEN_TYPESCRIPT)) or any(value is not None and not isinstance(value, str) for key, value in script.items() if key in (JsonKey.RUNABLE_SCRIPT, JsonKey.WRITTEN_TYPESCRIPT)):
                    raise ApiError("Incomplete workflow script content")
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
