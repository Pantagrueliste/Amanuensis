import os
import json
import re
import tempfile
import shutil
import logging

from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from rich.progress import Progress


def atomic_write(file_path, data):
    temp_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
    json.dump(data, temp_file, ensure_ascii=False, indent=4)
    temp_file.close()
    shutil.move(temp_file.name, file_path)


def write_to_file(batch, file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    data.update(batch)
    atomic_write(file_path, data)


class DynamicWordNormalization1:
    def __init__(self, config):
        self.config = config
        self.pattern = r"\w*\$\w*"
        self.lemmatizer = WordNetLemmatizer()
        self.machine_solutions_path = "data/machine_solution.json"
        self.unresolved_AWs_log = []
        self.load_machine_solutions()
        self.context_size = self.config.get("settings", "context_size")
        self.progress = Progress()
        self.task_id = self.progress.add_task("[cyan]Processing...", total=100)

    def update_progress(self, advance_by=1):
        self.progress.update(self.task_id, advance=advance_by)

    def load_machine_solutions(self):
        try:
            with open(self.machine_solutions_path, "r", encoding="utf-8") as file:
                contents = file.read().strip()
                if contents:
                    self.machine_solutions = json.loads(contents)
                    print(f"Loaded {len(self.machine_solutions)} machine solutions.")
                else:
                    self.machine_solutions = {}
        except FileNotFoundError:
            logging.error("Machine solutions file not found.")
            self.machine_solutions = {}
            self.save_json(self.machine_solutions_path, self.machine_solutions)

    def save_json(self, file_path, data):
        logging.info(f"Saving {len(data)} machine solutions to {file_path}")
        atomic_write(file_path, data)

    def extract_AWs(self, text):
        return re.findall(self.pattern, text)

    def process_AWs(self, text, filename, line_number, pattern):
        words = text.split()
        AWs = [word for word in words if "$" in word]
        context_size = self.context_size
        for AW in AWs:
            AW_index = words.index(AW)
            start_index = max(0, AW_index - context_size)
            end_index = min(len(words), AW_index + context_size + 1)
            context_words = words[start_index:end_index]

            solution = self.machine_solutions.get(AW)
            if not solution:
                solution = self.consult_wordnet(AW)
                if solution:
                    self.machine_solutions[AW] = solution
                    self.save_json(self.machine_solutions_path, self.machine_solutions)
                else:
                    self.log_unresolved_AW(
                        AW, filename, line_number, context_words, context_size
                    )

    def consult_wordnet(self, AW):
        """
        Consults WordNet to find a solution for the AW.
        """
        word_n = AW.replace("$", "n")
        if wordnet.synsets(word_n):
            return word_n
        word_m = AW.replace("$", "m")
        if wordnet.synsets(word_m):
            return word_m
        return None

    def log_unresolved_AW(self, AW, filename, line_number, context_words, context_size):
        """
        Logs the unresolved AWs to a file.
        """
        AW_index = context_words.index(AW)
        start_index = max(0, AW_index - self.context_size)
        end_index = min(len(context_words), AW_index + self.context_size + 1)
        context = " ".join(context_words[start_index:end_index])
        self.unresolved_AWs_log.append(
            {
                "filename": filename,
                "line": line_number,
                "column": AW_index,
                "unresolved_AW": AW,
                "context": context,
            }
        )

    def save_unresolved_AWs(self):
        logging.info(f"Saving {len(self.unresolved_AWs_log)} unresolved AWs.")
        unresolved_AWs_path = "data/unresolved_AW.json"
        self.save_json(unresolved_AWs_path, self.unresolved_AWs_log)

    def process_file(self, file_path, pattern):
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line_number, line in enumerate(lines, start=1):
                self.process_AWs(line, file_path, line_number, pattern)
        self.save_unresolved_AWs()

    def preprocess_directory(self, directory_path):
        total_files = self.total_files(directory_path)
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing files...", total=total_files)

            for root, _, files in os.walk(directory_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    self.process_file(file_path, self.pattern)
                    progress.update(task, advance=1)
            self.save_unresolved_AWs()

    def total_files(self, directory_path):
        count = 0
        for root, _, files in os.walk(directory_path):
            count += len(files)
        return count
