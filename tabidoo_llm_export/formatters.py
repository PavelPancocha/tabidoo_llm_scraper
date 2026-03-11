from __future__ import annotations

from typing import Optional

from .constants import MarkdownText, Newline, SanitizeDefaults, UiDefaults
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


class MarkdownRenderer:
    @staticmethod
    def wrap_typescript(content: str) -> str:
        return (
            f"{MarkdownText.TITLE_TSD}{Newline.DOUBLE}"
            f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}"
            f"{content.rstrip()}{Newline.LF}{MarkdownText.CODE_FENCE_END}{Newline.LF}"
        )
