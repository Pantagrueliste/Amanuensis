"""
Dynamic Word Normalization - Phase 2 (dynamic_word_normalization3.py)

This module serves as a higher-level handler for Dynamic Word Normalization,
incorporating GPT-based suggestions as an optional feature.
It orchestrates the activities of the lower-level DynamicWordNormalization2 class
and provides additional functionalities like managing difficult passages
and handling problematic files (i.e.: files that contain a high proportion of )

Modules:
- json: For parsing and dumping JSON files.
- os: For interacting with the operating system.
- logging: For logging activities and errors.
- Counter: For counting occurrences of items in collections.

Third-party Libraries:
- Config: Custom class for managing configurations.
- DynamicWordNormalization2: Lower-level class for handling Dynamic Word Normalization.
- GPTSuggestions: Class for generating GPT-based suggestions.
- atomic_write_json: Function for atomic JSON writes.

"""


import orjson
import os
from collections import Counter

from atomic_update import atomic_write_json
from config import Config
from dynamic_word_normalization2 import DynamicWordNormalization2
from gpt_suggestions import GPTSuggestions
from json import JSONDecodeError
from logging_config import get_logger


class DynamicWordNormalization3:
    def __init__(self, config, difficult_passages_file='data/difficult_passages.json', user_solution_file='data/user_solution.json'):
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing DynamicWordNormalization3 with user_solution_file: " + user_solution_file)
        self.console = None
        self.config = Config()
        use_gpt = self.config.get_openai_integration('gpt_suggestions')
        if use_gpt == True:
            self.gpt4 = GPTSuggestions(config)
        else:
            self.gpt4 = None
        self.dwn2 = DynamicWordNormalization2(config)
        self.input_path = self.config.get("paths", "input_path")
        self.difficult_passages_file = difficult_passages_file
        self.user_solution_file = user_solution_file
        self.difficult_passages = self.load_difficult_passages()

    def load_difficult_passages(self):
        try:
            with open(self.difficult_passages_file, 'rb') as f:  # Assuming you've set this variable
                return orjson.loads(f.read())
        except FileNotFoundError:
            if self.console:
                self.console.print(f"[red]Error:[/red] File '{self.difficult_passages_file}' not found.")
            return []
        except JSONDecodeError:
            if self.console:
                self.console.print(f"[red]Error:[/red] Malformed JSON in file '{self.difficult_passages_file}'.")
            return []

    @staticmethod
    def word_count_in_file(file_path):
        with open(file_path, 'r') as f:
            return len(f.read().split())

    def print_ascii_bar_chart(self, data, title):
        if not data:
            self.logger.warning("No data available for bar chart.")
            return  # Exit the function if no data is provided

        counter = Counter(data)
        longest_label_length = max(map(len, data.keys()))
        increment = max(counter.values()) // 25 + 1

        print(title)
        for label, count in counter.items():
            bar_chunks, remainder = divmod(int(count * 8 / increment), 8)
            bar = '█' * bar_chunks
            if remainder > 0:
                bar += chr(ord('█') + (8 - remainder))
            bar = bar or '▏'
            print(f'{label.rjust(longest_label_length)} ▏ {int(count * 100):#4d} {bar}')

    def analyze_difficult_passages(self):
        difficulties_per_file = {}
        ratios_per_file = {}

        # Count the frequency of each filename in difficult_passages
        filenames = [entry['file_name'] for entry in self.difficult_passages]
        filename_counts = Counter(filenames)

        for file, difficulties_count in filename_counts.items():
            if self.input_path is None:
                raise ValueError("input_path is not set.")
            file_path = os.path.join(self.input_path, file)
            if os.path.exists(file_path):
                total_words = DynamicWordNormalization3.word_count_in_file(file_path)

                difficulties_per_file[file] = difficulties_count
                ratios_per_file[file] = difficulties_count / total_words if total_words else 0.0

        # Sorting files by the ratio of difficult passages to total words
        sorted_ratios = {k: v for k, v in sorted(ratios_per_file.items(), key=lambda item: item[1], reverse=True)}

        # Filtering files by ratio and limiting to the top 10
        filtered_ratios = {k: v for k, v in sorted_ratios.items() if v >= 0.0002}  # 0.02% as a decimal
        top_10_ratios = dict(list(filtered_ratios.items())[:10])

        # Print ASCII bar charts for the top 10
        self.print_ascii_bar_chart(top_10_ratios, "Top 10 Files by Ratio of Difficult Passages to Total Words:")

        return difficulties_per_file, top_10_ratios

    def handle_problematic_files(self, top_10_ratios):
        for file, ratio in top_10_ratios.items():
            print(f"File: {file}, Ratio: {ratio:.4f}")
            choice = input("Choose an option: [D]iscard or [F]ix: ").strip().upper()

            if choice == 'D':
                self.discard_file(file)
            elif choice == 'F':
                self.fix_file(file) # fix fix_file
            else:
                print("Invalid choice. Skipping this file.")

    def discard_file(self, file):
        # Remove the file from self.difficult_passages to discard it from further processing
        if file in self.difficult_passages:
            del self.difficult_passages[file]
        self.logger.warning(f"Discarded file: {file}")
        print(f"Discarded file: {file}")

    def handle_word_with_user_input(self, word, context, file_name, line_number, column):
        # Call the handle_user_input method of DynamicWordNormalization2
        correct_word = self.dwn2.handle_user_input(word, context, file_name, line_number, column)

        # Update the user solution with the correct word
        self.update_user_solution(word, correct_word)

        return correct_word


    def accept_gpt4_suggestion(self, word, suggestion):
        # Update the user_solution.json with the accepted GPT-4 suggestion
        self.logger.debug("Accessing dynamic_word_normalization3.py at line 148: # Update the user_solution.json with the accepted GPT-4 suggestion")
        self.update_user_solution(word, suggestion)

    def reject_gpt4_suggestion(self):
        # Do nothing and move on
        pass

    def manual_fix(self, word, user_input):
        # Update the user_solution.json with the user's manual input
        self.update_user_solution(word, user_input)

    def update_user_solution(self, word, solution):
        # Prepare the data
        data_to_write = {word: solution}

        # Atomic update to user_solution.json
        self.logger.debug("Accessing dynamic_word_normalization3.py at line 163: # Atomic update to user_solution.json")
        self.logger.debug("Accessing dynamic_word_normalization3.py at line 164: atomic_write_json(data_to_write, 'user_solution.json')")

        atomic_write_json(data_to_write, self.user_solution_file)

    def get_gpt4_suggestions(self, passage):
        if self.gpt4:
            suggestions = self.gpt4.get_suggestions(passage)
            return suggestions
        else:
            return None
