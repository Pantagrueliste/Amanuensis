import json
import os
import logging
from collections import Counter
from config import Config

class DynamicWordNormalization3:
    def __init__(self, difficult_passages_file='difficult_passages.json', user_solution_file='user_solution.json', input_folder=None):
        self.config = Config()
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

def fix_file(self, file):
        print(f"Fixing file: {file}")
        logging.info(f"Fixing file: {file}")

        difficult_passages = self.difficult_passages.get(file, [])

        # TODO: Reuse logic from DynamicWordNormalization2 to get initial solutions

        for passage in difficult_passages:
            print(f"Fixing passage: {passage}")
            logging.info(f"Fixing passage: {passage}")

            # TODO: Fetch GPT-4 suggestions for the passage
            choice = input(f"Choose an option: [A]ccept GPT-4 suggestion, [R]eject, [M]anual fix: ").strip().upper()

            if choice == 'A':
                # TODO: Accept GPT-4 suggestion and update user_solution.json
                # self.update_user_solution(passage, gpt_suggestions)
                pass
            elif choice == 'R':
                # TODO: Reject GPT-4 suggestion, do nothing
                pass
            elif choice == 'M':
                # TODO: Allow user to manually fix the passage and update user_solution.json
                # self.update_user_solution(passage, manual_solution)
                pass
            else:
                print("Invalid choice. Skipping this passage.")
                logging.error("Invalid choice. Skipping this passage.")

def update_user_solution(self, passage, solution):
    # TODO: Implement atomic update to user_solution.json
