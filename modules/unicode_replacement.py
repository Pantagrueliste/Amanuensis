import orjson
import os
from multiprocessing import Pool
from time import time
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress

from config import Config


class UnicodeReplacement:
    def __init__(self, config: Config, num_workers: Optional[int] = None):
        self._initialize_config(config)
        self.log = []
        self.num_workers = num_workers

    def _initialize_config(self, config: Config):
        try:
            self.replacements_on = config.get("unicode_replacements", "replacements_on")
            self.characters_to_delete = config.get("unicode_replacements", "characters_to_delete")
            self.characters_to_replace = config.get("unicode_replacements", "characters_to_replace")
            self.output_path = config.get("paths", "output_path")
        except KeyError as e:
            raise ValueError(f"Missing key in config file: {e}")

    def replace(self, input_file_path: str):
        """Applies Unicode replacements on the given file and saves the modified text."""
        local_log = []
        with open(input_file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        modified_lines = [self._modify_line(line, i+1, input_file_path, local_log) for i, line in enumerate(lines)]
        self._write_output_file(input_file_path, modified_lines)
        return local_log

    def _modify_line(self, line: str, line_num: int, input_file_path: str, local_log: list) -> str:
        modified_line = line
        if self.replacements_on:
            modified_line = self._delete_chars(modified_line, line_num, input_file_path, local_log)
            modified_line = self._replace_chars(modified_line, line_num, input_file_path, local_log)
        return modified_line

    def _delete_chars(self, line: str, line_num: int, input_file_path: str, local_log: list) -> str:
        for char in self.characters_to_delete:
            if char in line:
                UnicodeReplacement.log_change(input_file_path, line_num, char, "deleted", local_log)
                line = line.replace(char, "")
        return line

    def _replace_chars(self, line: str, line_num: int, input_file_path: str, local_log: list) -> str:
        for original, replacement in self.characters_to_replace.items():
            if original in line:
                UnicodeReplacement.log_change(input_file_path, line_num, original, replacement, local_log)
                line = line.replace(original, replacement)
        return line

    def _write_output_file(self, input_file_path: str, modified_lines: List[str]):
        output_file_path = os.path.join(self.output_path, os.path.basename(input_file_path))
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.writelines(modified_lines)

    @staticmethod
    def log_change(input_file_path: str, line_num: int, original: str, replacement: str, local_log: list = None):
        """
        Log a replacement or deletion to the log list.
        """
        log_entry = {
            "timestamp": time(),
            "file_name": os.path.basename(input_file_path),
            "line_number": line_num,
            "original": original,
            "replacement": replacement,
        }
        local_log.append(log_entry)

    def save_log(self):
        """
        Save the log list to a JSON file in the logs directory.
        """
        with open('logs/unicode_replacement_log.json', 'wb') as f:
            f.write(orjson.dumps(self.log))

    def print_summary(self):
        """
        Print a summary of the Unicode Replacement phase based on the log attribute.
        """
        console = Console()

        deleted_count = sum(1 for entry in self.log if entry["replacement"] == "deleted")
        replaced_count = sum(1 for entry in self.log if entry["replacement"] != "deleted")
        files_changed_count = len(set(entry["file_name"] for entry in self.log))

        console.print(f"\n[bold cyan]Summary of Unicode Replacement Phase:[/bold cyan]")
        console.print(f"[green]Characters deleted:[/green] {deleted_count}")
        console.print(f"[green]Characters replaced:[/green] {replaced_count}")
        console.print(f"[green]Files Changed:[/green] {files_changed_count}")

    def process_files(self, input_files):
        """Apply Unicode replacements on multiple files using multiprocessing."""
        global_log = []
        with Progress() as progress:
            task = progress.add_task("[green]Processing...", total=len(input_files))
            with Pool() as pool:
                for local_log in pool.imap_unordered(self.replace, input_files):
                    global_log.extend(local_log)
                    progress.update(task, advance=1)
        self.log = global_log
        self.save_log()
        self.print_summary()
