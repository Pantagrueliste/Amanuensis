"""
Dynamic Word Normalization - Phase 1.2 (dynamic_word_normalization2.py)

This module handles phase 1.2 of Dynamic Word Normalization. It focuses on unresolved
abbreviated words (aws) and provides a series of utilities to resolve them either via user
input or predefined solutions. It also maintains counters for tracking the resolution process
and logs difficult passages for further review.

Modules:
- json: For parsing and dumping JSON files.
- os: For interacting with the operating system.
- re: For regular expression operations.
- string: For string manipulations.

Third-party Libraries:
- prompt_toolkit: For enhancing the CLI experience.
- rich: For rich text and formatting in the console.

"""
import re
import orjson
import Levenshtein
import ijson

from Levenshtein import distance as lev_distance
from colorama import Fore
from prompt_toolkit import prompt
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress
from rich.theme import Theme
from json import JSONDecodeError
from logging_config import get_logger
from atomic_update import atomic_append_json


class UserQuitException(Exception):
    pass


class DynamicWordNormalization2:
    def __init__(self, config, unresolved_aws_path="data/unresolved_aw.json", ambiguous_aws=None):
        self.logger = get_logger(__name__)
        self.config = config
        if ambiguous_aws is None:
            ambiguous_aws = []

        if not unresolved_aws_path:
            unresolved_aws_path = self.config.unresolved_aw_path
        self.batch_size = config.get("settings", "batch_size", 1000)
        self.unresolved_aws_path = unresolved_aws_path
        self.unresolved_aws = self.load_unresolved_aws(unresolved_aws_path)
        self.ambiguous_aws = ambiguous_aws
        self.solved_aws_count = 0
        self.processed_files_count = 0
        self.remaining_aws_count = len(self.unresolved_aws)
        self.remaining_files_count = len(
            set([aw["filename"] for aw in self.unresolved_aws])
        )

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
            user_solution_path = self.config.get("data", "user_solution_path")
            with open(user_solution_path, 'rb') as f:
                self.existing_user_solutions = orjson.loads(f.read())
        except FileNotFoundError:
            self.existing_user_solutions = {}

        # Load existing machine solutions
        try:
            with open(self.config.machine_solution_path, 'rb') as f:
                self.existing_machine_solutions = orjson.loads(f.read())
        except FileNotFoundError:
            self.existing_machine_solutions = {}

    def load_unresolved_aws(self, file_path):
        """Load unresolved alternative words (aws) from the JSON file."""
        try:
            with open(file_path, 'rb') as f:
                return orjson.loads(f.read())
        except FileNotFoundError:
            self.logger.error(f"Unresolved aws file '{file_path}' not found.")
            return []
        except JSONDecodeError:
            self.console.print(f"[red]Error:[/red] Malformed JSON in file '{file_path}'.")
            return []

    def print_status(self):
        """Print the current status of the DWN1.2 phase."""
        total_aws = len(self.unresolved_aws)
        solved_aws = self.solved_aws_count

        self.console.rule("[green]Progress[/green]", style="green")
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
        ) as progress:
            task1 = progress.add_task("", total=total_aws)
            progress.update(task1, completed=solved_aws)
        self.console.print(f"[info]Solved words:[/info] {self.solved_aws_count}")
        self.console.print(f"[info]Remaining words:[/info] {self.remaining_aws_count}")
        self.console.print(
            f"[info]Processed files:[/info] {self.processed_files_count}"
        )
        self.console.print(
            f"[info]Remaining files:[/info] {self.remaining_files_count}"
        )
        self.console.rule(style="green")

    def update_user_solution(self, unresolved_aw, correct_word):
        user_solution_path = "data/user_solution.json"

        # Load existing user solutions
        try:
            with open('data/user_solution.json', 'rb') as f:
                self.existing_user_solutions = orjson.loads(f.read())
        except FileNotFoundError:
            self.existing_user_solutions = {}

        # Update the user solutions with the new solution
        self.existing_user_solutions[unresolved_aw] = correct_word

        # Write the updated user solutions back to the file
        atomic_append_json(self.existing_user_solutions, user_solution_path)

    def process_unresolved_aws(self, unresolved_aws_path):
        """Process unresolved aws by prompting the user for solutions."""
        # current_file = None
        batch = []

        # Stream-parse the unresolved_aws.json file
        with open(self.unresolved_aws_path, 'r') as file:
            unresolved_aws = ijson.items(file, 'item')
            for unresolved_aw in unresolved_aws:
                batch.append(unresolved_aw)

                # If batch size is reached, process the aws and reset the batch
                if len(batch) == self.batch_size:
                    self._process_batch(batch)
                    batch = []

        # Process any remaining aws in the last batch
        if batch:
            self._process_batch(batch)

    def _process_batch(self, batch):
        """Private method to handle processing of aws in the batch."""
        expected_keys = {"unresolved_aw", "context", "filename", "line", "column"}
        current_file = None

        for unresolved_aw in batch:
            if not isinstance(unresolved_aw, dict) or not expected_keys.issubset(unresolved_aw.keys()):
                self.logger.error(f"Unexpected item structure: {unresolved_aw}")
                continue

            word = self.remove_trailing_punctuation(unresolved_aw["unresolved_aw"])
            context = unresolved_aw["context"]
            file_name = unresolved_aw["filename"]
            line_number = unresolved_aw["line"]
            column = unresolved_aw["column"]

            if word in self.existing_user_solutions or word in self.existing_machine_solutions:
                self.console.print(f"[dim red]{word}[/dim red] [bright_black]solved.[/bright_black]")
                self.solved_aws_count += 1
                self.remaining_aws_count -= 1
                continue

            if word in self.ambiguous_aws:
                self.console.print(f"[dim red]{word}[/dim red] [bright_black]is ambiguous.[/bright_black]")
                self.log_difficult_passage(file_name, line_number, column, context, word)
                continue

            correct_word = self.handle_user_input(word, context, file_name, line_number, column)
            self.update_user_solution(word, correct_word)
            self.solved_aws_count += 1
            self.remaining_aws_count -= 1

            if current_file != file_name:
                self.processed_files_count += 1
                self.remaining_files_count -= 1
                current_file = file_name
            self.print_status()

    @staticmethod
    def remove_trailing_punctuation(word):
        # return re.sub(r'(\$?)[\.,;:!?(){}]$', r'\1', word)
        return re.sub(r"^[,;:!?(){}]|[,;:!?(){}]$", "", word)

    def generate_suggestions(self, unresolved_aw, threshold=3):
        best_suggestion = None
        min_distance = float("inf")

        # Combine user and machine solutions for comprehensive search
        all_solutions = {
            **self.existing_user_solutions,
            **self.existing_machine_solutions,
        }

        for existing_aw, solution in all_solutions.items():
            curr_distance = lev_distance(unresolved_aw, existing_aw)

            if curr_distance < min_distance and curr_distance <= threshold:
                min_distance = curr_distance
                best_suggestion = solution

        return best_suggestion

    def log_difficult_passage(self, file_name, line_number, column, context, abbreviated_word):
        """Log a difficult passage."""
        difficult_passages_path = self.config.get("data", "difficult_passages_path")

        # Load existing difficult passages
        try:
            with open(difficult_passages_path, 'rb') as f:
                difficult_passages = orjson.loads(f.read())
        except FileNotFoundError:
            difficult_passages = []

        # Append difficult passages
        difficult_passages.append(
            {
                "file_name": file_name,
                "line_number": line_number,
                "column": column,
                "context": context,
                "abbreviated_word": abbreviated_word
            }
        )

        # Write the updated difficult passages back to the file
        with open(difficult_passages_path, 'wb') as f:
            f.write(orjson.dumps(difficult_passages))

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
            correct_word_prompt = (f"[info]Enter '[/info][danger]n[/danger][info]' or '[/info][danger]m[/danger]["
                                   f"info]' to replace $, '[/info][danger]d[/danger][info]' to discard it\nEnter the "
                                   f"full replacement for '[/info][danger]{word}[/danger][info]' \nType '[/info]["
                                   f"danger]`[/danger][info]' if you don't know\nType '[/info][danger]quit[/danger]["
                                   f"info]' to exit:[/info]\n")

            # Print the prompt using Rich Console
            self.console.print(correct_word_prompt)

            # Use prompt_toolkit for user input
            correct_word = prompt("input: ")

            # Handle special commands
            if correct_word.lower() == "quit":
                raise UserQuitException()
            elif correct_word == "`":
                self.log_difficult_passage(file_name, line_number, column, context, word)
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
            distance = Levenshtein.distance(word.replace("$", ""), correct_word)
            if distance > word.count("$") + 1:
                self.console.print(
                    "[yellow]Your input seems significantly different from the original word. Please confirm if this "
                    "is correct.[/yellow]"
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
