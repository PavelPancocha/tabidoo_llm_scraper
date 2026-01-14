import fnmatch
import time
from pathlib import Path
from typing import List, Tuple


class FileConsolidator:
    START_DIR: Path = Path(__file__).resolve().parent
    FILE_TYPES: Tuple[str, ...] = (
        "*.py",
        "*.md",
        "*.toml",
        "*.txt",
        "*.yml",
        "*.html",
        "*.css",
        "*.js",
        "*.json",
        "*.ts"
    )
    OUTPUT_FILE: str = "consolidated_files.txt"
    OUTPUT_FILE_PATH: Path = START_DIR / OUTPUT_FILE
    IGNORED_FILES_DIRS: List[str] = [
        OUTPUT_FILE,
        "manage.py",
        ".*",
        "compile_mentor_files.py",
        "*.ini",
        "mobile/**",
        "node_modules/**",
        "static/**",
        "schema.*",
        OUTPUT_FILE,
    ]

    def consolidate_files(self) -> None:
        files_count = 0
        _start = time.perf_counter()
        try:
            initial_size: float = Path(self.OUTPUT_FILE).stat().st_size / 1024
        except FileNotFoundError:
            initial_size = 0
        with open(self.OUTPUT_FILE_PATH, "w") as outfile:
            for file_type in self.FILE_TYPES:
                for filename in self.START_DIR.glob("**/" + file_type):
                    print(f"Processing: {filename}...", end="")
                    if any(
                        fnmatch.fnmatch(str(filename.relative_to(self.START_DIR)), ignored)
                        for ignored in self.IGNORED_FILES_DIRS
                    ):
                        print(" Ignored.")
                        continue
                    outfile.write(f"# File name: {filename.relative_to(self.START_DIR)}\n")
                    try:
                        with open(filename, "r") as infile:
                            outfile.write(infile.read() + "\n")
                        outfile.write("-" * 40 + "\n\n")
                        files_count += 1
                    except Exception as e:
                        print(f"Error: {e}")
                    else:
                        print(" OK.")
        print(f"Processed {files_count} files. Consolidated content written to {self.OUTPUT_FILE}.")
        print(f"Elapsed time: {time.perf_counter() - _start:.2f} seconds.")
        resulting_file_size = Path(self.OUTPUT_FILE).stat().st_size / 1024
        diff = resulting_file_size - initial_size
        print(f"Resulting file size: {resulting_file_size:.2f} KB. (Diff: {diff:.2f} KB)")


if __name__ == "__main__":
    consolidator = FileConsolidator()
    consolidator.consolidate_files()
