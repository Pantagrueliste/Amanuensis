import os
import json
from multiprocessing import Pool
from time import time
from config import Config
from rich.progress import Progress

class UnicodeReplacement:
    def __init__(self, config):
        # Extract the necessary settings from the config object and store them as separate attributes
        self.replacements_on = config.get('unicode_replacements', 'replacements_on')
        self.characters_to_delete = config.get('unicode_replacements', 'characters_to_delete')
        self.characters_to_replace = config.get('unicode_replacements', 'characters_to_replace')
        self.output_path = config.get('paths', 'output_path')

        # Initialize the log
        self.log = []


    def replace(self, input_file_path):
        """
        Applies Unicode replacements on the given file and saves the modified text
        in a separate path specified in the configuration file.
        """
        with open(input_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified_lines = []
        for line_num, line in enumerate(lines, 1):
            modified_line = line

            if self.replacements_on:
                # Delete specified characters
                for char in self.characters_to_delete:
                    if char in modified_line:
                        self.log_change(input_file_path, line_num, char, "deleted")
                        modified_line = modified_line.replace(char, "")

                # Apply specified replacements
                for original, replacement in self.characters_to_replace.items():
                    if original in modified_line:
                        self.log_change(input_file_path, line_num, original, replacement)
                        modified_line = modified_line.replace(original, replacement)

            modified_lines.append(modified_line)

        # Prepare the output file path
        output_path = self.output_path
        file_name = os.path.basename(input_file_path)
        output_file_path = os.path.join(output_path, file_name)

        # Write the modified text to the output file
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)


    def log_change(self, file_path, line_num, original, replacement):
        """
        Log a replacement or deletion to the log list.
        """
        log_entry = {
            'timestamp': time(),
            'file_name': os.path.basename(file_path),
            'line_number': line_num,
            'original': original,
            'replacement': replacement
        }
        self.log.append(log_entry)

    def save_log(self):
        """
        Save the log list to a JSON file in the logs directory.
        """
        # Determine the base directory of the app
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, 'logs')

        # Ensure the logs directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file_path = os.path.join(log_dir, 'replacements_log.json')

        with open(log_file_path, 'w', encoding='utf-8') as file:
            json.dump(self.log, file, ensure_ascii=False, indent=4)


    def print_summary(self):
        """
        Print a summary of the Unicode Replacement phase based on the log attribute.
        """
        deleted_count = sum(1 for entry in self.log if entry['replacement'] == 'deleted')
        replaced_count = sum(1 for entry in self.log if entry['replacement'] != 'deleted')
        files_changed_count = len(set(entry['file_name'] for entry in self.log))

        print(f"\nSummary of Unicode Replacement Phase:")
        print(f"Number of Words Deleted: {deleted_count}")
        print(f"Number of Words Replaced: {replaced_count}")
        print(f"Number of Files Changed: {files_changed_count}")


    def process_files(self, input_files):
           """
           Apply Unicode replacements on multiple files using multiprocessing.
           """
           with Progress() as progress:
               task = progress.add_task("[green]Processing...", total=len(input_files))
               with Pool() as pool:
                   for _ in pool.imap_unordered(self.replace, input_files):
                       progress.update(task, advance=1)

           self.save_log()
           self.print_summary()

           print(f"Processed {len(input_files)} files. Check the replacements_log.json for details.")
