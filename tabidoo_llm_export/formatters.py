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
            sections.append(f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}")
            sections.append(block.code_ts or SanitizeDefaults.EMPTY)
            sections.append(f"{MarkdownText.CODE_FENCE_END}{Newline.LF}")

        if workflows:
            sections.append(f"{MarkdownText.TITLE_WORKFLOW}{Newline.DOUBLE}")
            for idx, wf in enumerate(workflows, start=UiDefaults.INDEX_START):
                sections.append(
                    MarkdownText.WORKFLOW_PREFIX.format(index=idx, name=wf.workflow) + Newline.LF
                )
                sections.append(MarkdownText.TRIGGERS_LABEL.format(value=wf.triggers) + Newline.LF)
                sections.append(f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}")
                sections.append(wf.code_ts or SanitizeDefaults.EMPTY)
                sections.append(f"{MarkdownText.CODE_FENCE_END}{Newline.LF}")

        if custom_scripts:
            sections.append(f"{MarkdownText.TITLE_CUSTOM}{Newline.DOUBLE}")
            for idx, cs in enumerate(custom_scripts, start=UiDefaults.INDEX_START):
                sections.append(
                    MarkdownText.CUSTOM_PREFIX.format(index=idx, name=cs.name) + Newline.LF
                )
                sections.append(MarkdownText.NAMESPACE_LABEL.format(value=cs.namespace) + Newline.LF)
                sections.append(MarkdownText.INTERFACE_LABEL.format(value=cs.interface) + Newline.LF)
                sections.append(f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}")
                sections.append(cs.script or SanitizeDefaults.EMPTY)
                sections.append(f"{MarkdownText.CODE_FENCE_END}{Newline.LF}")

        return Newline.LF.join(sections)


class MarkdownRenderer:
    @staticmethod
    def wrap_typescript(content: str) -> str:
        return (
            f"{MarkdownText.TITLE_TSD}{Newline.DOUBLE}"
            f"{MarkdownText.CODE_FENCE_TS}{Newline.LF}"
            f"{content.rstrip()}{Newline.LF}{MarkdownText.CODE_FENCE_END}{Newline.LF}"
        )
