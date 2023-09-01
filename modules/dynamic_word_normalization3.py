import json
import os
import logging
from collections import Counter
from config import Config
from dynamic_word_normalization2 import DynamicWordNormalization2
from gpt_suggestions import GPTSuggestions
from atomic_update import atomic_write_json


class DynamicWordNormalization3:
    def __init__(self, config, difficult_passages_file='data/difficult_passages.json', user_solution_file='user_solution.json', input_folder=None):
        self.config = Config()
        use_gpt = self.config.get_openai_integration('gpt_suggestions')
        if use_gpt == True:
            self.gpt4 = GPTSuggestions(config)
        else:
            self.gpt4 = None
        self.dwn2 = DynamicWordNormalization2()
        self.input_path = self.config.get("paths", "input_path")
        self.difficult_passages_file = difficult_passages_file
        self.user_solution_file = user_solution_file
        self.difficult_passages = self.load_difficult_passages()

    def load_difficult_passages(self):
        with open(self.difficult_passages_file, 'r', encoding="utf-8") as f:
            return json.load(f)

    def word_count_in_file(self, file_path):
        with open(file_path, 'r') as f:
            return len(f.read().split())

    def print_ascii_bar_chart(self, data, title):
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
                print(f'{label.rjust(longest_label_length)} ▏ {count:#4d} {bar}')

    def analyze_difficult_passages(self):
        difficulties_per_file = {}
        ratios_per_file = {}

        for file, difficulties in self.difficult_passages.items():
            file_path = os.path.join(self.input_path, file)
            if os.path.exists(file_path):
                total_words = self.word_count_in_file(file_path)
                difficulties_count = len(difficulties)

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
                        self.fix_file(file)
                    else:
                        print("Invalid choice. Skipping this file.")

        def discard_file(self, file):
                # Remove the file from self.difficult_passages to discard it from further processing
                if file in self.difficult_passages:
                    del self.difficult_passages[file]
                print(f"Discarded file: {file}")

        def get_initial_solutions(self, word):
            # Reuse the logic from DynamicWordNormalization2 to get initial solutions
            initial_solution = self.dwn2.get_solution_for_word(word)
            return initial_solution

        def get_gpt4_suggestions(self, passage):
            # Fetch GPT-4 suggestions for the passage
            suggestions = self.gpt4.get_suggestions(passage)
            return suggestions

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
            # Prepare the data
            data_to_write = {word: solution}

            # Atomic update to user_solution.json
            atomic_write_json(data_to_write, 'user_solution.json')

        def get_gpt4_suggestions(self, passage):
                if self.gpt4:
                    suggestions = self.gpt4.get_suggestions(passage)
                    return suggestions
                else:
                    return None
