import json
import os
import re
import string

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich.progress import BarColumn, Progress
from colorama import Fore, Style
import Levenshtein
from Levenshtein import distance as lev_distance
from atomic_update import atomic_write_json



# def atomic_write_json(file_path, data):
#     temp_file_path = file_path + ".tmp"
#     with open(temp_file_path, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)
#     os.rename(temp_file_path, file_path)


class UserQuitException(Exception):
    pass


class DynamicWordNormalization2:
    def __init__(self, unresolved_AWs_path="data/unresolved_AW.json", ambiguous_AWs=[]):
        self.unresolved_AWs = self.load_unresolved_AWs(unresolved_AWs_path)
        self.ambiguous_AWs = ambiguous_AWs
        self.solved_AWs_count = 0
        self.processed_files_count = 0
        self.remaining_AWs_count = len(self.unresolved_AWs)
        self.remaining_files_count = len(
            set([aw["filename"] for aw in self.unresolved_AWs])
        )
        from atomic_update import atomic_write_json


        custom_theme = Theme(
            {
                "info": "rgb(128,128,128)",
                "warning": "rgb(255,192,0)",
                "danger": "rgb(255,0,0)",
                "neutral": "rgb(128,128,128)",
            }
        )
        self.console = Console(theme=custom_theme)

        # Load existing user solutions
        try:
            with open("data/user_solution.json", "r", encoding="utf-8") as file:
                self.existing_user_solutions = json.load(file)
        except FileNotFoundError:
            self.existing_user_solutions = {}

        # Load existing machine solutions
        try:
            with open("data/machine_solution.json", "r", encoding="utf-8") as file:
                self.existing_machine_solutions = json.load(file)
        except FileNotFoundError:
            self.existing_machine_solutions = {}

    def load_unresolved_AWs(self, file_path):
        """Load unresolved alternative words (AWs) from the JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Unresolved AWs file '{file_path}' not found.")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Malformed JSON in file '{file_path}' at line {e.lineno}, column {e.colno}",
                e.doc,
                e.pos,
            )

    def print_status(self):
        """Print the current status of the DWN1.2 phase."""
        total_AWs = len(self.unresolved_AWs)
        solved_AWs = self.solved_AWs_count
        remaining_AWs = self.remaining_AWs_count

        self.console.rule("[green]Progress[/green]", style="green")
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
        ) as progress:
            task1 = progress.add_task("", total=total_AWs)
            progress.update(task1, completed=solved_AWs)
        self.console.print(f"[info]Solved words:[/info] {self.solved_AWs_count}")
        self.console.print(f"[info]Remaining words:[/info] {self.remaining_AWs_count}")
        self.console.print(
            f"[info]Processed files:[/info] {self.processed_files_count}"
        )
        self.console.print(
            f"[info]Remaining files:[/info] {self.remaining_files_count}"
        )
        self.console.rule(style="green")

    def update_user_solution(self, unresolved_AW, correct_word):
        user_solution_path = "data/user_solution.json"

        # Load existing user solutions
        try:
            with open(user_solution_path, "r", encoding="utf-8") as file:
                user_solutions = json.load(file)
        except FileNotFoundError:
            user_solutions = {}

        # Update the user solutions with the new solution
        self.existing_user_solutions[unresolved_AW] = correct_word

        # Write the updated user solutions back to the file
        atomic_write_json(self.existing_user_solutions, user_solution_path)

    def process_unresolved_AWs(self):
        """Process unresolved AWs by prompting the user for solutions."""
        current_file = None

        try:
            with open("data/user_solution.json", "r", encoding="utf-8") as file:
                self.existing_user_solutions = json.load(file)
        except FileNotFoundError:
            self.existing_user_solutions = {}

        for unresolved_AW in self.unresolved_AWs:
            # Extracting words with "$" using regular expression
            pattern = r"\w*\$+\w*"
            AWs = re.findall(pattern, unresolved_AW["context"])
            word = DynamicWordNormalization2.remove_trailing_punctuation(
                unresolved_AW["unresolved_AW"]
            )

            full_update_needed = True

            if word in self.existing_user_solutions:
                self.console.print(
                    f"[dim red]{word}[/dim red] [bright_black]solved.[/bright_black]"
                )
                self.solved_AWs_count += 1
                self.remaining_AWs_count -= 1
                full_update_needed = False
                continue

            if word in self.ambiguous_AWs:
                self.console.print(
                    f"[dim red]{word}[/dim red] [bright_black]solved.[/bright_black]"
                )
                continue

            context = unresolved_AW["context"]
            file_name = unresolved_AW["filename"]
            line_number = unresolved_AW["line"]
            column = unresolved_AW["column"]

            # Check if the word is ambiguous and should be logged as a difficult passage
            if word in self.ambiguous_AWs:
                self.log_difficult_passage(file_name, line_number, column, context)
                continue

            # Skip the word if it already has a user-defined solution
            if word in self.existing_user_solutions:
                continue

            # Handle user input for unresolved_AW
            correct_word = self.handle_user_input(
                word, context, file_name, line_number, column
            )

            # Update user solutions
            self.update_user_solution(word, correct_word)

            # Update counters and print status
            self.solved_AWs_count += 1
            self.remaining_AWs_count -= 1

            # Update counters for files, if we have moved on to a new file
            file_name = unresolved_AW["filename"]

            if current_file != file_name:
                self.processed_files_count += 1
                self.remaining_files_count -= 1
                current_file = file_name
            self.print_status()

    @staticmethod
    def remove_trailing_punctuation(word):
        # return re.sub(r'(\$?)[\.,;:!?(){}]$', r'\1', word)
        return re.sub(r"^[\.,;:!?(){}]|[\.,;:!?(){}]$", "", word)

    def generate_suggestions(self, unresolved_AW, threshold=3):
        best_suggestion = None
        min_distance = float("inf")

        # Combine user and machine solutions for comprehensive search
        all_solutions = {
            **self.existing_user_solutions,
            **self.existing_machine_solutions,
        }

        for existing_AW, solution in all_solutions.items():
            curr_distance = lev_distance(unresolved_AW, existing_AW)

            if curr_distance < min_distance and curr_distance <= threshold:
                min_distance = curr_distance
                best_suggestion = solution

        return best_suggestion

    def log_difficult_passage(self, file_name, line_number, column, context):
        """Log a difficult passage."""
        difficult_passages_path = "data/difficult_passages.json"

        # Load existing difficult passages
        try:
            with open(difficult_passages_path, "r", encoding="utf-8") as file:
                difficult_passages = json.load(file)
        except FileNotFoundError:
            difficult_passages = []

        # Append difficult passages
        difficult_passages.append(
            {
                "file_name": file_name,
                "line_number": line_number,
                "column": column,
                "context": context,
            }
        )

        # Write the updated difficult passages back to the file
        with open(difficult_passages_path, "w", encoding="utf-8") as file:
            json.dump(difficult_passages, file, ensure_ascii=False, indent=4)

    def handle_user_input(self, word, context, file_name, line_number, column):
        while True:
            message1 = f"[info]Could not find a match for '[/info][danger]{word}[/danger][info]'[/info]"
            message2 = f"[info]Found in file '{file_name}' at line {line_number}[/info]"
            self.console.print(f"{message1}\n{message2}")
            best_suggestion = self.generate_suggestions(word)
            if best_suggestion:
                self.console.print(
                    f"[info]Closest known word:[/info] [warning]{best_suggestion}[/warning]"
                )

            highlighted_context = re.sub(
                r"\b" + re.escape(word) + r"(\W)?",
                f"[danger]{word}\\1[/danger]",
                context,
            )
            self.console.print(f"[info]Context:[/info]")
            self.console.print(
                Panel.fit(highlighted_context, border_style="bright_black")
            )
            correct_word_prompt = f"[info]Enter '[/info][danger]n[/danger][info]' or '[/info][danger]m[/danger][info]' to replace $, '[/info][danger]d[/danger][info]' to discard it\nEnter the full replacement for '[/info][danger]{word}[/danger][info]' \nType '[/info][danger]`[/danger][info]' if you don't know\nType '[/info][danger]quit[/danger][info]' to exit:[/info]\n"

            # Print the prompt using Rich Console
            self.console.print(correct_word_prompt)

            # Use prompt_toolkit for user input
            correct_word = prompt("input: ")

            # Handle special commands
            if correct_word.lower() == "quit":
                raise UserQuitException()
                break
            elif correct_word == "`":
                self.log_difficult_passage(file_name, line_number, column, context)
                self.console.print(
                    "[green]Difficult passage logged. Please continue with the next word.[/green]"
                )
                return word
            elif correct_word.lower() == "n":
                correct_word = word.replace("$", "n")
            elif correct_word.lower() == "m":
                correct_word = word.replace("$", "m")
            elif correct_word.lower() == "d":
                correct_word = word.replace("$", "")

            # Validate user's input
            lev_distance = Levenshtein.distance(word.replace("$", ""), correct_word)
            if lev_distance > word.count("$") + 1:
                self.console.print(
                    "[yellow]Your input seems significantly different from the original word. Please confirm if this is correct.[/yellow]"
                )
                confirmation = input(
                    "Type 'yes' to confirm, 'no' to input again: "
                ).lower()
                while confirmation not in ["yes", "no"]:
                    confirmation = input(
                        Fore.RED
                        + "Invalid response. Type 'yes' to confirm, 'no' to input again: "
                    ).lower()
                if confirmation == "no":
                    continue

            break
        return correct_word
