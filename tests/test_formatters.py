from __future__ import annotations

import unittest

from tabidoo_llm_export.formatters import LlmFormatter
from tabidoo_llm_export.models import ExtractedCode, ExtractedCodeFragment


class LlmFormatterCodeBlockTests(unittest.TestCase):
    def test_renders_html_fragment_with_html_fence(self) -> None:
        extracted = ExtractedCode(
            app_id="app-1",
            app_name="Example (example)",
            fragments=[
                ExtractedCodeFragment(
                    table="orders",
                    field_name="summaryWidget",
                    code_js="",
                    code_ts="",
                    code_html="<section>{{ total }}</section>",
                )
            ],
        )

        rendered = LlmFormatter().format(extracted, workflows=None, custom_scripts=None)

        self.assertIn("```html", rendered)
        self.assertIn("<section>{{ total }}</section>", rendered)
        self.assertNotIn("```javascript\n\n```", rendered)

    def test_prefers_typescript_over_javascript_for_script_fragments(self) -> None:
        extracted = ExtractedCode(
            app_id="app-1",
            app_name="Example (example)",
            fragments=[
                ExtractedCodeFragment(
                    table="orders",
                    field_name="refresh",
                    code_js="console.log('js')",
                    code_ts="console.log('ts')",
                )
            ],
        )

        rendered = LlmFormatter().format(extracted, workflows=None, custom_scripts=None)

        self.assertIn("```typescript", rendered)
        self.assertIn("console.log('ts')", rendered)
        self.assertNotIn("console.log('js')", rendered)


if __name__ == "__main__":
    unittest.main()
