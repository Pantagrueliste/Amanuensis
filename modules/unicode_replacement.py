import orjson
import os
import re
from multiprocessing import Pool
from time import time
from typing import List, Optional, Dict, Tuple

from rich.console import Console
from rich.progress import Progress

from config import Config


class UnicodeReplacement:
    def __init__(self, config: Config, num_workers: Optional[int] = None):
        self._initialize_config(config)
        self.log = []
        self.num_workers = num_workers
        
        # Common early modern abbreviation markers
        self.default_abbr_markers = {
            # Macrons (overlines)
            'ā': 'a$', 'ē': 'e$', 'ī': 'i$', 'ō': 'o$', 'ū': 'u$', 'n̄': 'n$', 'm̄': 'm$',
            # Tildes
            'ã': 'a$', 'ẽ': 'e$', 'ĩ': 'i$', 'õ': 'o$', 'ũ': 'u$', 'ñ': 'n$',
            # Superscript letters
            'ᵃ': 'a$', 'ᵉ': 'e$', 'ⁱ': 'i$', 'ᵒ': 'o$', 'ᵘ': 'u$', 'ʳ': 'r$', 'ˢ': 's$', 'ᵗ': 't$',
            # Other common abbreviation markers
            'ꝑ': 'p$', 'ꝓ': 'p$', 'ꝗ': 'q$', 'ꝙ': 'q$', 'ꝯ': 'con$',
            # Period marks
            '.mo': '.mo', '.ma': '.ma', '.mi': '.mi',
        }
        
        # Add any configured abbr markers
        self.abbr_markers = {**self.default_abbr_markers}
        if config.get("unicode_replacements", "additional_abbr_markers", None):
            self.abbr_markers.update(config.get("unicode_replacements", "additional_abbr_markers"))

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
            # Process abbreviation markers
            modified_line = self._replace_abbr_markers(modified_line, line_num, input_file_path, local_log)
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
        
    def _replace_abbr_markers(self, line: str, line_num: int, input_file_path: str, local_log: list) -> str:
        """Replace abbreviation markers with standard $ notation for dictionary compatibility."""
        for marker, replacement in self.abbr_markers.items():
            if marker in line:
                UnicodeReplacement.log_change(input_file_path, line_num, marker, replacement, local_log)
                line = line.replace(marker, replacement)
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
        
    @staticmethod
    def normalize_abbreviation(abbr_text: str) -> str:
        """
        Normalize an abbreviation from a TEI document to match the dictionary format.
        
        Args:
            abbr_text: The raw abbreviation text from TEI
            
        Returns:
            Normalized abbreviation text with $ notation
        """
        # Handle specific TEI g elements with abbreviation markers
        # Process <g ref="char:cmbAbbrStroke">̄</g> pattern which is a combining macron
        g_pattern = r'<g ref="char:cmbAbbrStroke">([^<]+)</g>'
        
        # First check if there's a g element with the combining macron
        if re.search(g_pattern, abbr_text):
            # Process it and convert to $ notation
            # Extract the base letter before the g element
            parts = re.split(g_pattern, abbr_text)
            normalized = ''
            
            for i in range(0, len(parts) - 1, 2):
                base_letter = parts[i][-1] if parts[i] else ''
                if base_letter:
                    # Remove the base letter from its position and add with $ suffix
                    normalized += parts[i][:-1] + base_letter + '$'
                else:
                    normalized += parts[i]
            
            # Add the last part if it exists
            if len(parts) % 2 == 1:
                normalized += parts[-1]
                
            return normalized
            
        # Handle <g ref="char:abque"/> pattern
        abque_pattern = r'<g ref="char:abque"/>'
        if re.search(abque_pattern, abbr_text):
            # Replace with a standard 'que' abbreviation marker
            return re.sub(abque_pattern, 'q$', abbr_text)
            
        # Common abbreviation markers
        markers = {
            # Macrons (overlines)
            'ā': 'a$', 'ē': 'e$', 'ī': 'i$', 'ō': 'o$', 'ū': 'u$', 'n̄': 'n$', 'm̄': 'm$',
            # Tildes
            'ã': 'a$', 'ẽ': 'e$', 'ĩ': 'i$', 'õ': 'o$', 'ũ': 'u$', 'ñ': 'n$',
            # Superscript letters
            'ᵃ': 'a$', 'ᵉ': 'e$', 'ⁱ': 'i$', 'ᵒ': 'o$', 'ᵘ': 'u$', 'ʳ': 'r$', 'ˢ': 's$', 'ᵗ': 't$',
            # Other common abbreviation markers
            'ꝑ': 'p$', 'ꝓ': 'p$', 'ꝗ': 'q$', 'ꝙ': 'q$', 'ꝯ': 'con$',
        }
        
        # Replace each marker
        normalized = abbr_text
        for marker, replacement in markers.items():
            normalized = normalized.replace(marker, replacement)
            
        # Handle common Latin abbreviations with period (e.g., Ill.mo)
        # Convert them to use $ notation for dictionary lookups
        period_regex = r'\.([a-z]{2})$'
        normalized = re.sub(period_regex, lambda m: f'${m.group(1)}', normalized)
        
        return normalized
        
    @staticmethod
    def denormalize_expansion(abbr_text: str, expansion: str) -> str:
        """
        Convert an expansion back to the style matching the original abbreviation.
        
        Args:
            abbr_text: Original abbreviation text
            expansion: The expansion text
            
        Returns:
            Expansion text styled to match the original
        """
        # Currently just returns the plain expansion
        # Could be extended to maintain case patterns or other stylistic elements
        return expansion