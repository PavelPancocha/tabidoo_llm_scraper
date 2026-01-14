from __future__ import annotations

from pathlib import Path

from .constants import Encoding, Format, OutputSuffix, Separator
from .env import Sanitizer
from .formatters import MarkdownRenderer
from .models import AppSummary


class OutputWriter:
    def write(self, out_dir: Path, app: AppSummary, tsd: str, llm_md: str) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Sanitizer.sanitize(app.name)
        schema_name = Format.OUTPUT_FILE.format(
            name=safe_name,
            separator=Separator.FILE,
            suffix=OutputSuffix.SCHEMA,
        )
        scripts_name = Format.OUTPUT_FILE.format(
            name=safe_name,
            separator=Separator.FILE,
            suffix=OutputSuffix.SCRIPTS,
        )
        schema_path = out_dir / schema_name
        scripts_path = out_dir / scripts_name
        schema_path.write_text(MarkdownRenderer.wrap_typescript(tsd), encoding=Encoding.UTF8)
        scripts_path.write_text(llm_md, encoding=Encoding.UTF8)
        return schema_path, scripts_path
