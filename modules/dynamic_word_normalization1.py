import os
import json
import re

from nltk.stem import WordNetLemmatizer
from rich.progress import Progress
from atomic_update import atomic_write_json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from logging_config import get_logger

logger = get_logger(__name__)


# def save_json_data(self):
#     """
#     Save pending json data to json disk.
#     """
#     for filename, data in self.pending_json_data.items():
#         atomic_write_json(data, filename)
#     logger.info("Saved pending json data to disk.")

def save_json_data(self):
    """
    Save pending json data to json disk.
    """
    for filename, data in self.pending_json_data.items():
        # Ensure filename has the correct directory structure
        correct_path = os.path.join('data/', filename)
        atomic_write_json(data, correct_path)
    logger.info("Saved pending json data to disk.")


def save_json(file_path, data):
    logger.info(f"Saving {len(data)} machine solutions to {file_path}")
    atomic_write_json(data, file_path)


class DynamicWordNormalization1:
    def __init__(self, config):
        self.config = config
        self.pattern = r"\w*\$\w*"
        self.lemmatizer = WordNetLemmatizer()
        self.machine_solutions_path = self.config.machine_solution_path
        self.unresolved_AWs_path = self.config.unresolved_AW_path
        self.unresolved_AWs_log = []

        data_directory = os.path.dirname(self.machine_solutions_path)
        if not os.path.exists(data_directory):
            os.makedirs(data_directory)

        self.load_machine_solutions()

        self.context_size = self.config.get("settings", "context_size")
        self.progress = Progress()
        self.task_id = self.progress.add_task("[cyan]Processing...", total=100)
        self.compiled_pattern = re.compile(self.pattern)
        self.wordnet_lock = Lock()

    @property
    def machine_solutions(self):
        if self._machine_solutions is None:
            self.load_machine_solutions()
        return self._machine_solutions

    @machine_solutions.setter
    def machine_solutions(self, value):
        self._machine_solutions = value

    def update_progress(self, advance_by=1):
        self.progress.update(self.task_id, advance=advance_by)

    def load_machine_solutions(self):
        try:
            with open(self.machine_solutions_path, "r", encoding="utf-8") as file:
                contents = file.read().strip()
                self.machine_solutions = json.loads(contents) if contents else {}
        except FileNotFoundError:
            logger.error("Machine solutions file not found.")
            self.machine_solutions = {}

    def extract_AWs(self, text):
        self.compiled_pattern.findall(text)

    def process_AWs(self, text, filename, line_number):
        words = text.split()
        AWs = {word: True for word in words if "$" in word}
        context_size = self.context_size
        for AW in AWs:
            try:
                clean_AW = re.sub(r"[,;:!?(){}]", "", AW)
                AW_index = words.index(AW)
                start_index = max(0, AW_index - context_size)
                end_index = min(len(words), AW_index + context_size + 1)
                context_words = words[start_index:end_index]

                solution = self.machine_solutions.get(AW)
                if not solution:
                    try:
                        solution = self.consult_wordnet(AW)
                    except Exception as e:
                        logger.error(f"Error consulting WordNet for AW '{AW}': {e}")
                        solution = None

                    if solution:
                        self.machine_solutions[AW] = solution
                        save_json(self.machine_solutions_path, self.machine_solutions)
                    else:
                        self.log_unresolved_AW(
                            AW, filename, line_number, context_words
                        )
            except Exception as e:
                logger.error(f"Error processing AWs in file {filename} on line {line_number}: {e}")

    @lru_cache(maxsize=40960)
    def consult_wordnet(self, AW):
        """
        Consults WordNet to find a solution for the AW.
        """
        with self.wordnet_lock:
            from nltk.corpus import wordnet

            word_n = AW.replace("$", "n")
            if wordnet.synsets(word_n):
                return word_n
            word_m = AW.replace("$", "m")
            if wordnet.synsets(word_m):
                return word_m
        return None

    def log_unresolved_AW(self, AW, filename, line_number, context_words):
        """
        Logs the unresolved AWs to a file.
        """
        AW_index = context_words.index(AW)  # Use the original AW
        start_index = max(0, AW_index - self.context_size)
        end_index = min(len(context_words), AW_index + self.context_size + 1)
        context = " ".join(context_words[start_index:end_index])
        sanitized_AW = re.sub(r"[,;:!?(){}]", "", AW)

        self.unresolved_AWs_log.append(
            {
                "filename": filename,
                "line": line_number,
                "column": AW_index,
                "unresolved_AW": sanitized_AW,
                "context": context,
            }
        )

    def save_unresolved_AWs(self):
        logger.info(f"Saving {len(self.unresolved_AWs_log)} unresolved AWs.")
        unresolved_AWs_path = self.config.get("data", "unresolved_AWs_path")
        save_json(unresolved_AWs_path, self.unresolved_AWs_log)

    def process_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line_number, line in enumerate(lines, start=1):
                self.process_AWs(line, file_path, line_number)
        self.save_unresolved_AWs()

    def total_files(self, directory_path):
        count = 0
        for root, _, files in os.walk(directory_path):
            count += len(files)
        return count

    def process_file_wrapper(self, args):
        file_path, pattern = args
        self.process_file(file_path)

    def preprocess_directory(self, directory_path):
        logger.setLevel(50)
        total_files = self.total_files(directory_path)

        with ThreadPoolExecutor() as executor, Progress() as progress:
            task = progress.add_task("[cyan]Analyzing files...", total=total_files)
            file_args = []

            for root, _, files in os.walk(directory_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_args.append((file_path, self.pattern))

            results = executor.map(self.process_file_wrapper, file_args)

            for _ in results:
                progress.update(task, advance=1)

            self.save_unresolved_AWs()
