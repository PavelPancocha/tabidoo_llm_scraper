from __future__ import annotations

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from unittest.mock import patch

from rich.console import Console

from tabidoo_llm_export.api import TsdFetcher
from tabidoo_llm_export.errors import ApiError
from tabidoo_llm_export.extractor import ScriptExtractor
from tabidoo_llm_export.formatters import LlmFormatter, MarkdownRenderer, TablesFormatter
from tabidoo_llm_export.models import AppSummary, ExtractedCode
from tabidoo_llm_export.output import OutputWriter
from tabidoo_llm_export.runner import ExportRunner
from tabidoo_llm_export.stats import StatsBuilder
from tabidoo_llm_export.ui import Ui


class DefinitionApi:
    def __init__(self, definitions: dict[Optional[str], str], fail: bool = False) -> None:
        self.definitions = definitions
        self.fail = fail

    def get_typescript_definition(self, app_id: str, schema_id: Optional[str] = None) -> str:
        if self.fail:
            raise ApiError("definition failed")
        return self.definitions[schema_id]


class DiskSchemaTests(unittest.TestCase):
    def check_output_and_stats(self, source: Path, expected: str, root: Path) -> None:
        app = AppSummary("app-1", "Example", "example")
        schema, tables, scripts = OutputWriter().write(root / "out", app, source, "tables\r\nč", "scripts\n😀")
        assert schema is not None
        self.assertEqual(schema.read_bytes(), MarkdownRenderer.wrap_typescript(expected).encode("utf-8"))
        self.assertEqual(tables.read_bytes(), "tables\r\nč".encode("utf-8"))
        self.assertEqual(scripts.read_bytes(), "scripts\n😀".encode("utf-8"))
        stats = StatsBuilder.build({"tables": []}, ExtractedCode("app-1", "Example", []), [], [], source, "tables\r\nč", "scripts\n😀")
        self.assertEqual((stats.schema_lines, stats.schema_bytes), (len(expected.splitlines()), len(expected.encode("utf-8"))))
        self.assertEqual((stats.tables_md_lines, stats.tables_md_bytes), (len("tables\r\nč".splitlines()), len("tables\r\nč".encode("utf-8"))))
        self.assertEqual((stats.llm_lines, stats.llm_bytes), (len("scripts\n😀".splitlines()), len("scripts\n😀".encode("utf-8"))))

    def test_numbered_spools_preserve_legacy_join_and_empty_last_definition(self) -> None:
        for definitions in [("", "", ""), ("  α\r\n😀\vline\u2028", "", "\t\n\u2003"), ("", "middle\x1cnext", "last\r\n")]:
            with self.subTest(definitions=definitions), TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "schema.ts"
                tables = [{"id": str(i), "internalNameApi": f"table-{i}"} for i in range(len(definitions))]
                api = DefinitionApi({str(i): content for i, content in enumerate(definitions)})
                TsdFetcher(api).fetch("app-1", {"tables": tables}, source)  # type: ignore[arg-type]
                expected = "\n\n".join(part for i, content in enumerate(definitions) for part in (f"// Table: table-{i} ({i})", content.rstrip())).rstrip() + "\n"
                self.assertEqual(source.read_bytes(), expected.encode("utf-8"))
                self.assertEqual(list(root.iterdir()), [source], "Numbered spools must be removed")
                self.check_output_and_stats(source, expected, root)

    def test_fallback_preserves_all_splitlines_and_unicode_rstrip_at_chunk_boundaries(self) -> None:
        contents = ["", "\r\n", "\x1f", "\t\u2003\n", "a\rb\r\nc\nd\ve\ff\x1cg\x1dh\x1ei\x85j\u2028k\u2029l", "x" * 65_535 + "\r\n😀č\u2028tail" + "\u2003" * 65_537, "x" * 65_536 + "tail", "x" * 65_535 + "\r", "😀" * 65_535 + "\r\n"]
        for content in contents:
            with self.subTest(length=len(content)), TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "schema.ts"
                TsdFetcher(DefinitionApi({None: content})).fetch("app-1", {"tables": []}, source)  # type: ignore[arg-type]
                self.assertEqual(source.read_bytes(), content.encode("utf-8"))
                self.check_output_and_stats(source, content, root)

    def test_failed_fetch_removes_spools_and_does_not_publish_a_partial_schema(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ApiError, "definition failed"):
                TsdFetcher(DefinitionApi({}, fail=True)).fetch("app-1", {"tables": [{"id": "0"}, {"id": "1"}]}, root / "schema.ts")  # type: ignore[arg-type]
            self.assertEqual(list(root.iterdir()), [])
            with patch("tabidoo_llm_export.api.Path.write_bytes", side_effect=OSError("disk full")), self.assertRaisesRegex(OSError, "disk full"):
                TsdFetcher(DefinitionApi({"0": "test"})).fetch("app-1", {"tables": [{"id": "0"}]}, root / "schema.ts")  # type: ignore[arg-type]
            self.assertEqual(list(root.iterdir()), [])

    def test_runner_requires_schema_and_cleans_temporary_files(self) -> None:
        app = AppSummary("app-1", "Example", "example")
        app_full = {"id": "app-1", "name": "Example", "internalName": "example", "tables": [{"id": "0", "internalNameApi": "orders", "items": []}]}
        definition = "export interface Test { title: '😀č' }\r\n"

        class ExportApi(DefinitionApi):
            system_table_counts = {name: {"expected": 0, "fetched": 0} for name in ("wascenarios", "customScripts", "b7e89080-6bb2-4870-9e0f-7d7d491d9c7e")}

            def get_user(self) -> dict[str, str]:
                return {}

            def list_apps(self) -> list[AppSummary]:
                return [app]

            def get_app_full(self, app_id: str) -> dict[str, object]:
                return app_full

            def get_table_data(self, app_id: str, table: str) -> list[dict[str, object]]:
                return []

        for fail in (False, True):
            with self.subTest(fail=fail), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "example-schema.md").write_text("stale", encoding="utf-8")
                ui = Ui(Console(file=io.StringIO()))
                destinations: list[Path] = []
                fetch = TsdFetcher.fetch

                def capture_fetch(fetcher: TsdFetcher, app_id: str, data: dict[str, object], destination: Path) -> None:
                    destinations.append(destination)
                    fetch(fetcher, app_id, data, destination)

                with patch("tabidoo_llm_export.runner.TabidooApi", return_value=ExportApi({"0": definition}, fail)), patch.object(TsdFetcher, "fetch", capture_fetch), patch.object(ui, "show_stats") as show_stats:
                    if fail:
                        with self.assertRaisesRegex(ApiError, "definition failed"):
                            ExportRunner(ui, "https://example.invalid", "test", "en", 1, False).run("app-1", root, True)
                    else:
                        schema, tables, scripts = ExportRunner(ui, "https://example.invalid", "test", "en", 1, False).run("app-1", root, True)
                expected = "// Table: orders (0)\n\n" + definition.rstrip() + "\n"
                if fail:
                    self.assertEqual((root / "example-schema.md").read_text(), "stale")
                    show_stats.assert_not_called()
                else:
                    self.assertEqual(schema.read_bytes(), MarkdownRenderer.wrap_typescript(expected).encode("utf-8"))
                    self.assertEqual(show_stats.call_args.args[0].schema_bytes, len(expected.encode("utf-8")))
                    self.assertEqual(tables.read_bytes(), TablesFormatter().format(app_full).encode("utf-8"))
                    extracted = ScriptExtractor().extract(app_full)
                    self.assertEqual(scripts.read_bytes(), LlmFormatter().format(extracted, [], []).encode("utf-8"))
                self.assertEqual(len(destinations), 1)
                self.assertFalse(destinations[0].parent.exists(), "Runner must remove its private scratch directory")
                self.assertEqual(len(list(root.iterdir())), 1 if fail else 4)


if __name__ == "__main__":
    unittest.main()
