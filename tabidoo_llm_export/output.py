from __future__ import annotations

from pathlib import Path

from .constants import Encoding, Format, MarkdownText, Newline, OutputSuffix, Separator
from .env import Sanitizer
from .models import AppSummary


class OutputWriter:
    def write(
        self,
        out_dir: Path,
        app: AppSummary,
        schema_md: Path | None,
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
            with schema_path.open("wb") as output, schema_md.open("r", encoding=Encoding.UTF8, newline="") as source:
                output.write(f"{MarkdownText.TITLE_TSD}{Newline.DOUBLE}{MarkdownText.CODE_FENCE_TS}{Newline.LF}".encode(Encoding.UTF8))
                last_content_end = output.tell()
                for chunk in iter(lambda: source.read(65_536), ""):
                    offset = output.tell()
                    output.write(chunk.encode(Encoding.UTF8))
                    trimmed = chunk.rstrip()
                    if trimmed:
                        last_content_end = offset + len(trimmed.encode(Encoding.UTF8))
                output.seek(last_content_end)
                output.truncate()
                output.write(f"{Newline.LF}{MarkdownText.CODE_FENCE_END}{Newline.LF}".encode(Encoding.UTF8))
        else:
            if schema_path.exists():
                schema_path.unlink()
            schema_path = None
        tables_path.write_text(tables_md, encoding=Encoding.UTF8)
        scripts_path.write_text(llm_md, encoding=Encoding.UTF8)
        return schema_path, tables_path, scripts_path
