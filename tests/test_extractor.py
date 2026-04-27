from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
