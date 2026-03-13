from __future__ import annotations

from pathlib import Path

from .constants import Encoding, Format, OutputSuffix, Separator
from .env import Sanitizer
from .formatters import MarkdownRenderer
from .models import AppSummary


class OutputWriter:
    def write(
        self,
        out_dir: Path,
        app: AppSummary,
        schema_md: str | None,
        tables_md: str,
        llm_md: str,
    ) -> tuple[Path | None, Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Sanitizer.sanitize(app.name)
        schema_name = Format.OUTPUT_FILE.format(
            name=safe_name,
            separator=Separator.FILE,
            suffix=OutputSuffix.SCHEMA,
        )
        tables_name = Format.OUTPUT_FILE.format(
            name=safe_name,
            separator=Separator.FILE,
            suffix=OutputSuffix.TABLES,
        )
        scripts_name = Format.OUTPUT_FILE.format(
            name=safe_name,
            separator=Separator.FILE,
            suffix=OutputSuffix.SCRIPTS,
        )
        schema_path = out_dir / schema_name
        tables_path = out_dir / tables_name
        scripts_path = out_dir / scripts_name
        if schema_md is not None:
            schema_path.write_text(MarkdownRenderer.wrap_typescript(schema_md), encoding=Encoding.UTF8)
        else:
            if schema_path.exists():
                schema_path.unlink()
            schema_path = None
        tables_path.write_text(tables_md, encoding=Encoding.UTF8)
        scripts_path.write_text(llm_md, encoding=Encoding.UTF8)
        return schema_path, tables_path, scripts_path
