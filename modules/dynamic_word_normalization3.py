"""
Dynamic Word Normalization - Phase 2 (dynamic_word_normalization3.py)

This module serves as a higher-level handler for Dynamic Word Normalization,
incorporating GPT-based suggestions as an optional feature.
It orchestrates the activities of the lower-level DynamicWordNormalization2 class
and provides additional functionalities like managing difficult passages
and handling problematic files (i.e.: files that contain a high proportion of
unresolved Abbreviated Words)

Modules:
- orjson: For parsing and dumping JSON files.
- os: For interacting with the operating system.
- logging: For logging activities and errors.
- Counter: For counting occurrences of items in collections.

Third-party Libraries:
- Config: Custom class for managing configurations.
- DynamicWordNormalization2: Lower-level class for handling Dynamic Word Normalization.
- GPTSuggestions: Class for generating GPT-based suggestions.

"""

import orjson
import os
import math

from collections import Counter
from config import Config
from dynamic_word_normalization2 import DynamicWordNormalization2
from gpt_suggestions import GPTSuggestions
from json import JSONDecodeError
from logging_config import get_logger
from atomic_update import atomic_append_json

class DynamicWordNormalization3:
    def __init__(self, config, difficult_passages_file='data/difficult_passages.json', user_solution_file='data/user_solution.json'):
        self.logger = get_logger(__name__)
        self.console = None
        self.config = Config()
        use_gpt = self.config.get_openai_integration('gpt_suggestions')
        if use_gpt:
            self.gpt4 = GPTSuggestions(config)
        else:
            self.gpt4 = None
        self.dwn2 = DynamicWordNormalization2(config)
        self.input_path = self.config.get("paths", "input_path")
        self.difficult_passages_file = difficult_passages_file
        self.user_solution_file = user_solution_file
        self.difficult_passages = self.load_difficult_passages()

    def load_difficult_passages(self):
        self.logger.info(f"Attempting to load difficult passages from {self.difficult_passages_file}")
        try:
            with open(self.difficult_passages_file, 'rb') as f:
                data = orjson.loads(f.read())
                self.logger.info("Successfully loaded difficult passages.")
                return data
        except FileNotFoundError:
            error_msg = f"File '{self.difficult_passages_file}' not found."
            self.logger.error(error_msg)
            if self.console:
                self.console.print(f"[red]Error:[/red] {error_msg}")
            return []
        except JSONDecodeError as e:
            error_msg = f"Malformed JSON in file '{self.difficult_passages_file}': {e}"
            self.logger.error(error_msg)
            if self.console:
                self.console.print(f"[red]Error:[/red] {error_msg}")
            return []

    def word_count_in_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return len(f.read().split())
        except IOError as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return 0


    def analyze_difficult_passages(self):
        self.logger.info("Starting analysis of difficult passages.")
        self.logger.info(f"Total difficult passages loaded: {len(self.difficult_passages)}")

        normalized_input_path = os.path.normpath(self.input_path) + os.sep
        filtered_difficult_passages = [
            entry for entry in self.difficult_passages
            if os.path.normpath(entry['file_name']).startswith(normalized_input_path)
        ]
        self.logger.info(f"Difficult passages after filtering: {len(filtered_difficult_passages)}")

        if not filtered_difficult_passages:
            self.logger.warning("No matching difficult passages found for the specified input path.")
            print("Warning: No data found in the specified directory for analysis.")
            return {}, {}

        difficulties_per_file = {}
        ratios_per_file = {}
        filenames = [entry['file_name'] for entry in filtered_difficult_passages]
        filename_counts = Counter(filenames)

        self.logger.info("Calculating ratios of difficult passages to total words for each file.")
        self.logger.info("Entering the file analysis loop.")
        for file, difficulties_count in filename_counts.items():
            file_path = os.path.join(normalized_input_path, os.path.basename(file))
            self.logger.info(f"Checking file: {file_path}, exists: {os.path.exists(file_path)}")
            if os.path.exists(file_path):
                total_words = self.word_count_in_file(file_path)
                raw_ratio = difficulties_count / total_words if total_words else 0.0
                sqrt_ratio = math.sqrt(raw_ratio)

                difficulties_per_file[file] = difficulties_count
                ratios_per_file[file] = sqrt_ratio
                self.logger.info(f"File: {file}, Total Words: {total_words}, Difficulties Count: {difficulties_count}, Log Ratio: {sqrt_ratio:.4f}")

        self.logger.info("Ratios calculated. Sorting ratios for presentation.")
        sorted_ratios = {k: v for k, v in sorted(ratios_per_file.items(), key=lambda item: item[1], reverse=True)}

        self.print_ascii_bar_chart(sorted_ratios, "Files by Ratio of Difficult Passages to Total Words:")
        self.logger.info("Difficult passages ratios sorted and presented.")

        # Handle problematic files based on sorted ratios
        self.handle_problematic_files(sorted_ratios)

        return difficulties_per_file, sorted_ratios


    def handle_problematic_files(self, sorted_ratios):
            self.logger.info("Handling problematic files based on sorted ratios.")
            for file, ratio in sorted_ratios.items():
                self.logger.info(f"Presenting file '{file}' with difficulty ratio {ratio:.4f} to the user.")
                print(f"File: {file}, Ratio: {ratio:.4f}")
                choice = input("Choose [D]iscard, [F]ix or [G]PT Suggestion: ").strip().upper()

                if choice == 'D':
                    self.discard_file(file)
                elif choice == 'F':
                    self.fix_file(file)
                elif choice == 'G' and self.gpt4:
                    for passage in self.difficult_passages:
                        if passage['file_name'] == file:
                            suggestion = self.get_gpt_suggestion_for_passage(passage)
                            print(f"GPT Suggestion for {passage['abbreviated_word']}: {suggestion}")
                            user_decision = input("Do you want to accept this suggestion? (Y/N): ").strip().upper()
                            if user_decision == 'Y':
                                self.accept_gpt4_suggestion(passage['abbreviated_word'], suggestion)
                else:
                    print("Invalid choice. Skipping this file.")


    def get_gpt_suggestion_for_passage(self, passage):
        context = passage['context']  # Adjust this based on how your context is structured
        suggestion = self.gpt4.get_and_print_suggestion(context)
        return suggestion



    def print_ascii_bar_chart(self, data, title, scale_factor=1000):
        if not data:
            self.logger.warning("No enough data available for bar chart.")
            return

        counter = Counter(data)
        longest_label_length = max(map(len, data.keys()))

        print(title)
        for label, ratio in data.items():
            scaled_ratio = ratio * scale_factor
            formatted_ratio = f"{scaled_ratio:.2f}".rjust(6)  # Ensure ratio string has a consistent length
            bar = '█' * int(scaled_ratio)
            print(f'{label.rjust(longest_label_length)} ▏ {formatted_ratio} {bar}')

    def discard_file(self, file_path):
        try:
            discarded_dir = self.config.get("paths", "discarded_directory")  # Ensure this is in your config
            os.makedirs(discarded_dir, exist_ok=True)
            discarded_file_path = os.path.join(discarded_dir, os.path.basename(file_path))
            os.rename(file_path, discarded_file_path)
            self.logger.info(f"File {file_path} moved to {discarded_file_path}")
        except Exception as e:
            self.logger.error(f"Error discarding file {file_path}: {e}")


    def fix_file(self, file_path):
        self.logger.info(f"Fixing file: {file_path}")
        # Filter difficult passages for this file
        passages_to_fix = [p for p in self.difficult_passages if p['file_name'] == file_path]

        for passage in passages_to_fix:
            word = passage['abbreviated_word']
            context = passage['context']
            line_number = passage['line_number']
            column = passage['column']

            # Use DWN2's interface for user interaction
            corrected_word = self.dwn2.handle_user_input(word, context, file_path, line_number, column)

            # Update user_solution.json
            self.update_user_solution(word, corrected_word)

        self.logger.info(f"File {file_path} has been fixed.")


    def handle_word_with_user_input(self, word, context, file_name, line_number, column):
        # Call the handle_user_input method of DynamicWordNormalization2
        correct_word = self.dwn2.handle_user_input(word, context, file_name, line_number, column)

        # Update the user solution with the correct word
        self.update_user_solution(word, correct_word)

        return correct_word

    def accept_gpt4_suggestion(self, word, suggestion):
        # Update the user_solution.json with the accepted GPT-4 suggestion
        self.update_user_solution(word, suggestion)

    def reject_gpt4_suggestion(self):
        # Do nothing and move on
        pass

    def manual_fix(self, word, user_input):
        # Update the user_solution.json with the user's manual input
        self.update_user_solution(word, user_input)

    def update_user_solution(self, word, solution):
        # Prepare the new data
        new_data = {word: solution}

        # Atomic append to user_solution.json
        atomic_append_json(new_data, self.user_solution_file)

    def get_gpt4_suggestions(self, passage):
        if self.gpt4:
            suggestions = self.gpt4.get_suggestions(passage)
            return suggestions
        else:
            return None
