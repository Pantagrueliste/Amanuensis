import orjson
import os
from multiprocessing import Pool

from atomic_update import atomic_write_text
from config import Config
from logging import getLogger
from ahocorasick import Automaton

# Global variable for the FileProcessor instance
file_processor_instance = None


def load_solutions(file_path: str) -> dict:
    """Load solutions from a JSON file."""
    try:
        with open(file_path, 'rb') as f:
            return orjson.loads(f.read())
    except FileNotFoundError:
        return {}


def process_files_in_parallel(file_list: list, num_workers: int):
    """Process multiple files in parallel."""
    global file_processor_instance
    if not file_processor_instance:
        file_processor_instance = FileProcessor()

    # Utilize multiprocessing for parallel processing
    with Pool(num_workers) as p:
        p.map(process_file_wrapper, file_list)


# Wrapper function for parallel processing with an explicit initialization
def process_file_wrapper(file_path):
    global file_processor_instance
    if file_processor_instance is None:
        file_processor_instance = FileProcessor()
    return file_processor_instance.process_file(file_path)


class FileProcessor:
    def __init__(self, config_file='config.toml', user_solution_file='user_solution.json', machine_solution_file='machine_solution.json'):
        self.logger = getLogger(__name__)
        self.config = Config(config_file)
        self.output_path = self.config.get("paths", "output_path")
        self.user_solution_file = user_solution_file
        self.machine_solution_file = machine_solution_file
        self.user_solutions = load_solutions(file_path=self.user_solution_file)
        self.machine_solutions = load_solutions(file_path=self.machine_solution_file)
        self.automaton = self._build_automaton()

    def _build_automaton(self):
        """Builds the Aho-Corasick automaton from user and machine solutions."""
        automaton = Automaton()
        for abbreviation, replacement in self.user_solutions.items():
            automaton.add_word(abbreviation, replacement)
        for abbreviation, replacement in self.machine_solutions.items():
            automaton.add_word(abbreviation, replacement)
        automaton.make_automaton()
        return automaton

    def apply_abbreviations(self, text: str) -> str:
        """Applies the abbreviations to the text using Aho-Corasick algorithm."""
        result_parts = []
        last_end = 0

        for end, abbreviation in self.automaton.iter(text):
            replacement = self.user_solutions.get(abbreviation) or self.machine_solutions.get(abbreviation)
            start = end - len(abbreviation) + 1
            result_parts.append(text[last_end:start])
            result_parts.append(replacement)
            last_end = end + 1

        result_parts.append(text[last_end:])
        return ''.join(result_parts)

    def process_file(self, file_path: str):
        """Implement the logic to process a single file."""
        self.logger.debug(f"Processing file: {file_path}")
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            content = self.apply_abbreviations(content)

            output_file_path = os.path.join(self.output_path, os.path.basename(file_path))
            atomic_write_text(file_path=output_file_path, data=content)
            self.logger.debug(f"Output path: {self.output_path}")

        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")

    def parallel_process_files(self, files):
        with Pool() as pool:
            pool.map(self.process_file, files)

    def run(self):
        self.logger.debug("FastFileProcessor run method started.")
        # Load your AW mappings from JSON files
        user_solutions = self.user_solutions
        machine_solutions = self.machine_solutions

        # Create a set of all AWs to speed up lookup
        all_AWs = set(user_solutions.keys()).union(set(machine_solutions.keys()))

        # Get the list of all files in the directory specified in config.toml
        input_path = self.config.get("paths", "input_path")
        files_to_process = [os.path.join(input_path, f) for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]

        for file_path in files_to_process:
            with open(file_path, 'r') as f:
                content = f.read()

            # Check if this file contains any AWs
            if any(aw in content for aw in all_AWs):
                # Apply replacements
                for original, replacement in user_solutions.items():
                    content = content.replace(original, replacement)
                for original, replacement in machine_solutions.items():
                    content = content.replace(original, replacement)

                # Save the modified content
                output_file_path = os.path.join(self.output_path, os.path.basename(file_path))
                atomic_write_text(file_path=output_file_path, data=content)
