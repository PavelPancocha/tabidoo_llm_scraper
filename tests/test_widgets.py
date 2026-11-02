from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from rich.console import Console

from tabidoo_llm_export.api import TabidooApi
from tabidoo_llm_export.constants import ProgressStep, TableInternal
from tabidoo_llm_export.errors import ApiError
from tabidoo_llm_export.extractor import ScriptExtractor
from tabidoo_llm_export.formatters import LlmFormatter
from tabidoo_llm_export.models import AppSummary, ExtractedCode, ExtractedWidgetCodeFragment
from tabidoo_llm_export.runner import ExportRunner
from tabidoo_llm_export.ui import Ui

WIDGETS_TABLE = "b7e89080-6bb2-4870-9e0f-7d7d491d9c7e"


def widget(widget_id: str, widget_type: str, settings: dict[str, Any], ver: int | None = 3) -> dict[str, Any]:
    # Shape of a row from GET /v2/apps/{app}/tables/b7e89080-.../data (apps.trixit.cz, 2026-10-30).
    record: dict[str, Any] = {
        "id": widget_id,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-10-30T00:00:00Z",
        "fields": {"definitions": {"idWidgetType": widget_type, "settings": {"filters": {"conditions": {}}, **settings}, "style": {}}},
    }
    if ver is not None:
        record["ver"] = ver
    return record


def free_html(html: str = "", runable_html: str = "", ts: str = "", js: str = "") -> dict[str, Any]:
    return {
        "freeHtmlContent": {"writtenHtml": html, "runableHtml": runable_html},
        "freeHtmlInitScript": {"writtenTypeScript": ts, "runableSript": js},
        "headersI18n": {"en": ""},
    }


class WidgetExtractionTests(unittest.TestCase):
    def test_exports_widget_html_and_script_variants_sorted_by_id(self) -> None:
        rows = [
            widget("c-portal", "widgetNameFreeHtml", free_html("<main>portal</main>", ts="const a: number = 1;", js="var a = 1;"), ver=84),
            widget("a-ts-only", "widgetNameFreeHtml", free_html(ts="let x: string;")),
            widget("e-html-only", "widgetNameFreeHtml", {**free_html(runable_html="<p>runable</p>"), "headersI18n": {"en": "Akceptace", "cs": "Akceptace"}}),
            widget("b-js-only", "widgetNameFreeHtml", free_html(js="console.log(1)"), ver=None),
            widget("d-empty-free-html", "widgetNameFreeHtml", free_html()),
            widget("f-text", "widgetNameText", {"textI18n": {"en": "<p>5 kroků</p>"}}, ver=0),
            widget("g-text-empty", "widgetNameText", {"textI18n": {"en": "  "}}),
            widget("h-text-two-languages", "widgetNameText", {"textI18n": {"en": "<p>Hello</p>", "cs": "<p>Ahoj</p>"}}),
        ]

        widgets = ScriptExtractor().extract_widgets(rows)

        self.assertEqual(
            [w.widget_id for w in widgets],
            ["a-ts-only", "b-js-only", "c-portal", "e-html-only", "f-text", "h-text-two-languages"],
        )
        by_id = {w.widget_id: w for w in widgets}
        self.assertEqual(by_id["c-portal"], ExtractedWidgetCodeFragment(
            "c-portal", "widgetNameFreeHtml", "84", "", "<main>portal</main>", "const a: number = 1;", "var a = 1;"))
        self.assertEqual((by_id["a-ts-only"].html, by_id["a-ts-only"].code_ts, by_id["a-ts-only"].code_js), ("", "let x: string;", ""))
        self.assertEqual((by_id["b-js-only"].version, by_id["b-js-only"].code_js), ("", "console.log(1)"))
        self.assertEqual((by_id["e-html-only"].html, by_id["e-html-only"].header), ("<p>runable</p>", "Akceptace"))
        self.assertEqual((by_id["f-text"].widget_type, by_id["f-text"].version, by_id["f-text"].html), ("widgetNameText", "0", "<p>5 kroků</p>"))
        self.assertEqual(by_id["h-text-two-languages"].html, "<!-- cs -->\n<p>Ahoj</p>\n<!-- en -->\n<p>Hello</p>")

    def test_partial_system_projections_refuse_instead_of_looking_empty(self) -> None:
        extractor = ScriptExtractor()
        for fields in (None, {}, {"definition": {}}, {"definition": {"steps": [], "triggers": None}}):
            with self.subTest(fields=fields), self.assertRaises(ApiError):
                extractor.extract_workflows([{"id": "offline", "fields": fields}])
        self.assertEqual(extractor.extract_workflows([{"fields": {"definition": {"triggers": [], "steps": []}}}]), [])
        for method in (extractor.extract_custom_scripts, extractor.extract_widgets):
            for fields in (None, {}):
                with self.subTest(method=method.__name__, fields=fields), self.assertRaises(ApiError):
                    method([{"id": "offline", "fields": fields}])
        with self.assertRaisesRegex(ApiError, "custom script content"):
            extractor.extract_custom_scripts([{"fields": {"script": {}}}])
        with self.assertRaisesRegex(ApiError, "text widget content"):
            extractor.extract_widgets([widget("offline", "widgetNameText", {})])
        with self.assertRaisesRegex(ApiError, "HTML widget content"):
            extractor.extract_widgets([widget("offline", "widgetNameFreeHtml", {})])

    def test_empty_api_typescript_response_refuses(self) -> None:
        for content in ("", " \r\n\t", None):
            with self.subTest(content=content), self.assertRaises(ApiError):
                TabidooApi(SimpleClient({"content": content})).get_typescript_definition("offline", "offline-table")


class WidgetFormattingTests(unittest.TestCase):
    def test_widgets_section_follows_custom_scripts_with_html_and_typescript_blocks(self) -> None:
        widgets = [
            ExtractedWidgetCodeFragment("w-1", "widgetNameFreeHtml", "84", "Portál", "<main>x</main>", "const a = 1;", "var a = 1;"),
            ExtractedWidgetCodeFragment("w-2", "widgetNameFreeHtml", "", "", "", "", "console.log(2)"),
            ExtractedWidgetCodeFragment("w-3", "widgetNameText", "0", "", "<p>t</p>", "", ""),
        ]

        rendered = LlmFormatter().format(ExtractedCode("app-1", "Example", []), [], [], widgets)

        self.assertIn(
            "## Widgets\n\n\n### Widget 1: w-1\n\n**Type:** widgetNameFreeHtml\n**Version:** 84\n\n**Header:** Portál\n\n"
            "```html\n\n<main>x</main>\n```\n\n```typescript\n\nconst a = 1;\n```\n",
            rendered,
        )
        self.assertNotIn("var a = 1;", rendered, "TypeScript wins over the compiled script")
        self.assertIn("### Widget 2: w-2\n\n**Type:** widgetNameFreeHtml\n**Version:** \n\n```javascript\n\nconsole.log(2)\n```", rendered)
        self.assertIn("### Widget 3: w-3\n\n**Type:** widgetNameText\n**Version:** 0\n\n```html\n\n<p>t</p>\n```\n", rendered)
        self.assertNotIn("```javascript\n\n```", rendered)
        self.assertNotIn("## Widgets", LlmFormatter().format(ExtractedCode("app-1", "Example", []), [], []))


class FakeClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.paths: list[str] = []

    def get_json(self, path: str) -> dict[str, Any]:
        self.paths.append(path)
        if path.endswith("/count"):
            return {"data": {"count": len(self.rows)}}
        skip = int(path.rsplit("skip=", 1)[1])
        limit = int(path.split("limit=", 1)[1].split("&", 1)[0])
        return {"data": self.rows[skip:skip + limit]}


class SimpleClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def get_json(self, path: str) -> dict[str, Any]:
        return self.payload

    def post_json(self, path: str, body: object) -> dict[str, Any]:
        return self.payload


class WidgetFetchTests(unittest.TestCase):
    def test_app_detail_requires_complete_unique_table_metadata(self) -> None:
        valid = {"id": "t-1", "items": []}
        for tables in (None, {}, [None], [{"id": "t-1"}], [{"id": "t-1", "items": [None]}], [valid, valid]):
            with self.subTest(tables=tables):
                client = SimpleClient({"data": {"tables": tables}})
                with self.assertRaises(ApiError):
                    TabidooApi(client).get_app_full("app-1")
        self.assertEqual(TabidooApi(SimpleClient({"data": {"tables": []}})).get_app_full("app-1"), {"tables": []})

    def test_system_table_fetch_requires_count_and_every_unique_row(self) -> None:
        rows = [widget(f"w-{index:04d}", "widgetNameText", {}) for index in range(1001)]
        for count, page, error in (
            (1002, rows, "Incomplete"),
            (1001, rows[:1000] + [rows[0]], "Repeated"),
            (1001, rows[:1000] + [None], "Invalid"),
            ("1001", rows, "count"),
        ):
            with self.subTest(error=error):
                class Client(FakeClient):
                    def get_json(self, path: str) -> dict[str, Any]:
                        if path.endswith("/count"):
                            return {"data": {"count": count}}
                        if "skip=1000" in path:
                            return {"data": page[1000:]}
                        return {"data": page[:1000]}

                with self.assertRaisesRegex(ApiError, error):
                    TabidooApi(Client(rows)).get_table_data("app-1", TableInternal.WIDGETS)

        self.assertEqual(TabidooApi(FakeClient([])).get_table_data("app-1", TableInternal.WIDGETS), [])

    def test_system_table_http_error_propagates_before_or_after_first_page(self) -> None:
        rows = [widget(f"w-{index:04d}", "widgetNameText", {}) for index in range(1001)]
        for failing_path in ("/count", "skip=1000"):
            with self.subTest(failing_path=failing_path):
                class Client(FakeClient):
                    def get_json(self, path: str) -> dict[str, Any]:
                        if failing_path in path:
                            raise ApiError("GET failed")
                        return super().get_json(path)

                with self.assertRaisesRegex(ApiError, "GET failed"):
                    TabidooApi(Client(rows)).get_table_data("app-1", TableInternal.WIDGETS)

    def test_widgets_table_is_read_by_system_schema_id_across_pages(self) -> None:
        rows = [widget(f"w-{index:04d}", "widgetNameFreeHtml", free_html(ts="x")) for index in range(1001)]
        client = FakeClient(rows)

        fetched = TabidooApi(client).get_table_data("app-1", TableInternal.WIDGETS)  # type: ignore[arg-type]

        self.assertEqual(fetched, rows)
        self.assertEqual(client.paths, [
            f"/v2/apps/app-1/tables/{WIDGETS_TABLE}/data/count",
            f"/v2/apps/app-1/tables/{WIDGETS_TABLE}/data?limit=1000&skip=0",
            f"/v2/apps/app-1/tables/{WIDGETS_TABLE}/data?limit=1000&skip=1000",
        ])

    def test_runner_writes_widgets_into_scripts_and_counts_them(self) -> None:
        app = AppSummary("app-1", "Example", "example")
        app_full = {"id": "app-1", "name": "Example", "internalName": "example", "tables": [{"id": "first", "internalNameApi": "first", "items": []}, {"id": "second", "internalNameApi": "second", "items": []}]}
        rows = [widget("w-1", "widgetNameFreeHtml", free_html("<main/>", ts="const a = 1;"), ver=7)]
        workflows = [{"id": f"workflow-{i}", "fields": {"name": f"offline workflow {i}", "definition": {"triggers": [], "steps": [{"type": "jsScript", "data": {"script": {"runableSript": "void 0;"}}}]}}} for i in range(2)]
        custom = [{"id": f"custom-{i}", "fields": {"name": f"offline custom {i}", "namespace": f"offline{i}", "interface": "offline", "script": {"runableSript": "void 0;"}}} for i in range(2)]
        requested: list[str] = []

        class ExportApi:
            def __init__(self, client: object) -> None:
                self.system_table_counts: dict[str, dict[str, int]] = {}

            def get_user(self) -> dict[str, str]:
                return {}

            def list_apps(self) -> list[AppSummary]:
                return [app]

            def get_app_full(self, app_id: str) -> dict[str, object]:
                return app_full

            def get_table_data(self, app_id: str, table: str) -> list[dict[str, Any]]:
                requested.append(table)
                result = rows if table == TableInternal.WIDGETS else workflows if table == TableInternal.WORKFLOWS else custom
                self.system_table_counts[str(table)] = {"expected": len(result), "fetched": len(result)}
                return result

            def get_typescript_definition(self, app_id: str, schema_id: str | None = None) -> str:
                return "export {}"

        with TemporaryDirectory() as directory:
            ui = Ui(Console(file=io.StringIO()))
            with patch("tabidoo_llm_export.runner.TabidooApi", ExportApi), patch.object(ui, "show_stats") as show_stats:
                _, _, scripts = ExportRunner(ui, "https://example.invalid", "test", "en", 1, False).run("app-1", Path(directory), True)
            content = scripts.read_text(encoding="utf-8")
            completeness = json.loads((Path(directory) / "export-completeness.json").read_text())

        self.assertEqual(requested, [TableInternal.WORKFLOWS, TableInternal.CUSTOM_SCRIPTS, TableInternal.WIDGETS])
        self.assertIn("### Widget 1: w-1\n\n**Type:** widgetNameFreeHtml\n**Version:** 7", content)
        self.assertIn("### Workflow 2: offline workflow 1", content)
        self.assertIn("### Custom Script 2: offline custom 1", content)
        self.assertEqual(show_stats.call_args.args[0].widgets, 1)
        self.assertEqual(completeness, {
            "version": 1, "status": "PASS", "appId": "app-1",
            "tables": {"expected": 2, "tsdFetched": 2},
            "systemTables": {
                "wascenarios": {"expected": 2, "fetched": 2},
                "customScripts": {"expected": 2, "fetched": 2},
                WIDGETS_TABLE: {"expected": 1, "fetched": 1},
            },
            "fragments": {"tableScripts": 0, "workflows": 2, "customScripts": 2, "widgets": 1},
        })
        self.assertEqual(len(ProgressStep), 7)

        with TemporaryDirectory() as directory:
            ui = Ui(Console(file=io.StringIO()))
            with patch("tabidoo_llm_export.runner.TabidooApi", ExportApi), patch("tabidoo_llm_export.runner.LlmFormatter.format", return_value=""), self.assertRaisesRegex(ApiError, "Incomplete written"):
                ExportRunner(ui, "https://example.invalid", "test", "en", 1, False).run("app-1", Path(directory), True)
            self.assertFalse((Path(directory) / "export-completeness.json").exists())


if __name__ == "__main__":
    unittest.main()


class LegacyTextWidgetTests(unittest.TestCase):
    def test_legacy_text_key_is_exported(self) -> None:
        from tabidoo_llm_export.extractor import ScriptExtractor
        row = {"id": "w1", "ver": 1, "fields": {"definitions": {"idWidgetType": "widgetNameText", "settings": {"filters": [], "text": "<p>Hi</p>"}, "style": {}}}}
        [fragment] = ScriptExtractor().extract_widgets([row])
        self.assertEqual(fragment.html, "<p>Hi</p>")

    def test_text_widget_without_any_content_key_still_fails(self) -> None:
        from tabidoo_llm_export.errors import ApiError
        from tabidoo_llm_export.extractor import ScriptExtractor
        row = {"id": "w2", "fields": {"definitions": {"idWidgetType": "widgetNameText", "settings": {"filters": []}}}}
        with self.assertRaises(ApiError):
            ScriptExtractor().extract_widgets([row])
