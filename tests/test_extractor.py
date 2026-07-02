from __future__ import annotations

import json
import unittest

from tabidoo_llm_export.extractor import ScriptExtractor


class ScriptExtractorFieldScriptTests(unittest.TestCase):
    def test_extracts_current_field_type_scripts_and_html_content(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "orders",
                    "items": [
                        {
                            "name": "totalPrice",
                            "type": "calculated",
                            "metadata": {
                                "script": {
                                    "jsScript": "doo.model.price.value * doo.model.qty.value",
                                    "simplifiedScript": "Price * Quantity",
                                }
                            },
                        },
                        {
                            "name": "refresh",
                            "type": "button",
                            "metadata": {
                                "script": {
                                    "jsScript": "console.log('refresh')",
                                    "tsScript": "console.log('refresh' as string)",
                                }
                            },
                        },
                        {
                            "name": "summaryWidget",
                            "type": "freehtml",
                            "metadata": {
                                "freeHtmlInitScript": {
                                    "jsScript": "window.summaryReady = true",
                                    "tsScript": "window.summaryReady = true",
                                },
                                "freeHtmlContent": {
                                    "writtenHtml": "<section>{{ total }}</section>",
                                    "runableHtml": "<section>compiled</section>",
                                },
                            },
                        },
                    ],
                }
            ],
        }

        extracted = ScriptExtractor().extract(app_structure)

        self.assertEqual(len(extracted.fragments), 4)
        calculated, button, free_html_init, free_html_content = extracted.fragments
        self.assertEqual(calculated.field_name, "totalPrice")
        self.assertEqual(calculated.code_js, "doo.model.price.value * doo.model.qty.value")
        self.assertEqual(calculated.code_ts, "")
        self.assertEqual(button.code_ts, "console.log('refresh' as string)")
        self.assertEqual(free_html_init.code_js, "window.summaryReady = true")
        self.assertEqual(free_html_content.code_html, "<section>{{ total }}</section>")

    def test_extracts_legacy_field_type_scripts(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "legacy",
                    "items": [
                        {
                            "name": "legacyFormula",
                            "type": "calculatedfield",
                            "metadata": {"script": {"jsScript": "doo.model.amount.value"}},
                        },
                        {
                            "name": "legacyButton",
                            "type": "buttonform",
                            "metadata": {"script": {"jsScript": "await doo.alert.show('ok')"}},
                        },
                        {
                            "name": "legacyHtml",
                            "type": "freehtmlinput",
                            "metadata": {
                                "freeHtmlContent": {"runableHtml": "<div>legacy</div>"},
                            },
                        },
                    ],
                }
            ],
        }

        fragments = ScriptExtractor().extract(app_structure).fragments

        self.assertEqual([fragment.field_name for fragment in fragments], [
            "legacyFormula",
            "legacyButton",
            "legacyHtml",
        ])
        self.assertEqual(fragments[0].code_js, "doo.model.amount.value")
        self.assertEqual(fragments[1].code_js, "await doo.alert.show('ok')")
        self.assertEqual(fragments[2].code_html, "<div>legacy</div>")

    def test_skips_empty_field_scripts_and_html(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "empty_fields",
                    "items": [
                        {
                            "name": "emptyFormula",
                            "type": "calculated",
                            "metadata": {"script": {"name": "calculated-field"}},
                        },
                        {
                            "name": "emptyHtml",
                            "type": "freehtml",
                            "metadata": {
                                "freeHtmlInitScript": {},
                                "freeHtmlContent": {"writtenHtml": "  ", "runableHtml": ""},
                            },
                        },
                    ],
                }
            ],
        }

        extracted = ScriptExtractor().extract(app_structure)

        self.assertEqual(extracted.fragments, [])

    def test_extracts_legacy_table_scripts_without_form_logic_definitions(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "legacyTable",
                    "items": [],
                    "scripts": [
                        {
                            "name": "onModelLoad",
                            "jsScript": "legacy load js",
                            "tsScript": "legacy load ts",
                        }
                    ],
                }
            ],
        }

        fragments = ScriptExtractor().extract(app_structure).fragments

        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0].field_name, "onModelLoad")
        self.assertEqual(fragments[0].code_js, "legacy load js")
        self.assertEqual(fragments[0].code_ts, "legacy load ts")

    def test_extracts_json_part_form_logic_steps_without_duplicating_compat_scripts(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "developmentIdeas",
                    "items": [],
                    "scripts": [
                        {
                            "name": "onModelChange",
                            "jsScript": "compat js",
                            "tsScript": "compat ts",
                        }
                    ],
                    "jsonPart": json.dumps(
                        {
                            "jsScripts": [
                                {
                                    "name": "onModelChange",
                                    "runableSript": "jsonpart duplicate js",
                                    "writtenTypeScript": "jsonpart duplicate ts",
                                },
                                {
                                    "name": "beforeModelSave",
                                    "runableSript": "before save js",
                                    "writtenTypeScript": "before save ts",
                                },
                            ],
                            "formLogicDefinitions": [
                                {
                                    "type": "onChangeForm",
                                    "items": [
                                        {
                                            "clientId": "xh0qzf39qc",
                                            "title": "Step 2",
                                            "script": {
                                                "name": "onModelChange",
                                                "runableSript": "old step js",
                                                "writtenTypeScript": "old step ts",
                                            },
                                        },
                                        {
                                            "clientId": "x2z8p789yb",
                                            "title": "Demo: step 2",
                                            "script": {
                                                "name": "script",
                                                "runableSript": "// demo step 2",
                                                "writtenTypeScript": (
                                                    "(async (doo: IDoo) => {\n"
                                                    "    // demo step 2\n"
                                                    "})"
                                                ),
                                            },
                                        },
                                    ],
                                }
                            ],
                        }
                    ),
                }
            ],
        }

        fragments = ScriptExtractor().extract(app_structure).fragments
        by_name = {fragment.field_name: fragment for fragment in fragments}

        self.assertEqual([fragment.field_name for fragment in fragments].count("onModelChange"), 1)
        self.assertEqual(by_name["onModelChange"].code_ts, "compat ts")
        self.assertEqual(by_name["beforeModelSave"].code_ts, "before save ts")
        self.assertEqual(
            by_name["formLogicDefinitions / onChangeForm / Step 2 / onModelChange"].code_ts,
            "old step ts",
        )
        demo_step = by_name["formLogicDefinitions / onChangeForm / Demo: step 2 / script"]
        self.assertIn("demo step 2", demo_step.code_ts)
        self.assertIn("demo step 2", demo_step.code_js)

    def test_extracts_top_level_form_logic_definitions_from_public_app_payload(self) -> None:
        app_structure = {
            "id": "app-1",
            "name": "Example",
            "internalName": "example",
            "tables": [
                {
                    "id": "table-1",
                    "internalNameApi": "developmentIdeas",
                    "items": [],
                    "scripts": [],
                    "formLogicDefinitions": [
                        {
                            "type": "onChangeForm",
                            "items": [
                                {
                                    "clientId": "x2z8p789yb",
                                    "title": "Demo: step 2",
                                    "script": {
                                        "name": "script",
                                        "runableSript": "// demo step 2",
                                        "writtenTypeScript": "// demo step 2",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        fragments = ScriptExtractor().extract(app_structure).fragments

        self.assertEqual(len(fragments), 1)
        self.assertEqual(
            fragments[0].field_name,
            "formLogicDefinitions / onChangeForm / Demo: step 2 / script",
        )
        self.assertIn("demo step 2", fragments[0].code_ts)


if __name__ == "__main__":
    unittest.main()
