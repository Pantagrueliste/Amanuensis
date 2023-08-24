import json
import os

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from colorama import Fore, Style
import Levenshtein



class DynamicWordNormalization2:
    def __init__(self, unresolved_AWs_path='data/unresolved_AW.json'):
        # Load unresolved AWs
        self.unresolved_AWs = self.load_unresolved_AWs(unresolved_AWs_path)

        # Initialize counters
        self.solved_AWs_count = 0
        self.processed_files_count = 0
        self.remaining_AWs_count = len(self.unresolved_AWs)
        self.remaining_files_count = len(set([aw['filename'] for aw in self.unresolved_AWs]))

        # Create a Rich Console for better display
        self.console = Console()

        # Print the initial status
        self.print_status()

    def load_unresolved_AWs(self, file_path):
        """Load unresolved alternative words (AWs) from the JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Unresolved AWs file '{file_path}' not found.")

    def print_status(self):
        """Print the current status of the DWN1.2 phase."""
        self.console.print(f"Solved AWs: {self.solved_AWs_count}")
        self.console.print(f"Processed Files: {self.processed_files_count}")
        self.console.print(f"Remaining AWs: {self.remaining_AWs_count}")
        self.console.print(f"Remaining Files: {self.remaining_files_count}")

    def update_user_solution(self, unresolved_AW, correct_word):
        user_solution_path = 'data/user_solution.json'

        # Load existing user solutions
        try:
            with open(user_solution_path, 'r', encoding='utf-8') as file:
                user_solutions = json.load(file)
        except FileNotFoundError:
            user_solutions = {}

        # Update the user solutions with the new solution
        user_solutions[unresolved_AW] = correct_word

        # Write the updated user solutions back to the file
        with open(user_solution_path, 'w', encoding='utf-8') as file:
            json.dump(user_solutions, file, ensure_ascii=False, indent=4)


    def process_unresolved_AWs(self):
            """Process unresolved AWs by prompting the user for solutions."""
            for unresolved_AW in self.unresolved_AWs:
                word = unresolved_AW['AW']
                context = unresolved_AW['context']
                file_name = unresolved_AW['filename']
                line_number = unresolved_AW['line']
                column = unresolved_AW['column']

                correct_word = self.handle_user_input(word, context, file_name, line_number, column)
                self.update_user_solution(word, correct_word)

                # Update counters and print status
                self.solved_AWs_count += 1
                self.remaining_AWs_count -= 1
                if file_name not in [aw['filename'] for aw in self.unresolved_AWs[self.solved_AWs_count:]]:
                    self.processed_files_count += 1
                    self.remaining_files_count -= 1
                self.print_status()

    def log_difficult_passage(self, file_name, line_number, column, context):
        """Log a difficult passage to a JSON file."""
        difficult_passages_path = 'data/difficult_passages.json'

        # Load existing difficult passages
        try:
            with open(difficult_passages_path, 'r', encoding='utf-8') as file:
                difficult_passages = json.load(file)
        except FileNotFoundError:
            difficult_passages = []

        # Append difficult passages
        difficult_passages.append({
            'file_name': file_name,
            'line_number': line_number,
            'column': column,
            'context': context
        })

        # Write the updated difficult passages back to the file
        with open(difficult_passages_path, 'w', encoding='utf-8') as file:
            json.dump(difficult_passages, file, ensure_ascii=False, indent=4)


    def handle_user_input(self, word, context, file_name, line_number, column):
        """Handle user input for a specific unresolved AW."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            message1 = f"Could not find a match for '{Fore.RED + word + Style.RESET_ALL}'"
            message2 = f"in the dictionary after trying both replacements. Found in file '{file_name}' at line {line_number}."
            print(f"{Fore.LIGHTBLACK_EX}{message1}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}{message2}{Style.RESET_ALL}")
            print("Context: ", context)

            correct_word_prompt = HTML("<ansired>Please enter 'n' or 'm' to replace $, or enter the full replacement for '{}' or type '`' if you don't know:</ansired>\n".format(word))
            correct_word = prompt(correct_word_prompt)

            # Handle special commands
            if correct_word == '`':
                self.log_difficult_passage(file_name, line_number, column, context)
                print("Difficult passage logged. Please continue with the next word.")
                return word
            elif correct_word.lower() == 'n':
                correct_word = word.replace('$', 'n')
            elif correct_word.lower() == 'm':
                correct_word = word.replace('$', 'm')

            # Validate user's input
            lev_distance = Levenshtein.distance(word.replace('$', ''), correct_word)
            if lev_distance > word.count('$') + 1:
                print(Fore.YELLOW + "Your input seems significantly different from the original word. Please confirm if this is correct.")
                confirmation = input("Type 'yes' to confirm, 'no' to input again: ").lower()
                while confirmation not in ['yes', 'no']:
                    confirmation = input(Fore.RED + "Invalid response. Type 'yes' to confirm, 'no' to input again: ").lower()
                if confirmation == 'no':
                    continue
            break

        return correct_word
