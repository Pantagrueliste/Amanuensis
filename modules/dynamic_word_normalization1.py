import os
import json
import re
import toml
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from rich.progress import Progress
from rich.console import Console

batch = {}
batch_size = 10

def writer_process(queue, file_path):
    try:
        counter = 0
        while True:
            update = queue.get()
            if update == "DONE":
                if batch:
                    write_to_file(batch, file_path)
                break

            batch.update(update)
            counter += 1

            if counter >= batch_size:
                write_to_file(batch, file_path)
                batch.clear()
                counter = 0

    except Exception as e:
        print(f"Error in writer process: {e}")

def write_to_file(batch, file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    data.update(batch)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


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
            self.machine_solutions = {}
            self.save_json(self.machine_solutions_path, self.machine_solutions)

    def save_json(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def extract_AWs(self, text):
        return re.findall(self.pattern, text)

    def process_AWs(self, text, filename, line_number, pattern):
        words = re.findall(pattern, text)
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
        # print(f"Consulting WordNet for {AW}...") # debug
        word_n = AW.replace("$", "n")
        if wordnet.synsets(word_n):
            # print(f"Found solution: {word_n}")
            return word_n
        word_m = AW.replace("$", "m")
        if wordnet.synsets(word_m):
            # print(f"Found solution: {word_m}")
            return word_m
        return None

    def log_unresolved_AW(self, AW, filename, line_number, context_words, context_size):
        # print(f"Logging unresolved AW: {AW} in {filename}")
        AW_index = context_words.index(AW)
        start_index = max(0, AW_index - self.context_size)
        end_index = min(len(context_words) - 1, AW_index + self.context_size)
        context = " ".join(context_words[start_index : end_index + 1])
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
        unresolved_AWs_path = "data/unresolved_AW.json"
        self.save_json(unresolved_AWs_path, self.unresolved_AWs_log)

    def process_file(self, file_path, pattern):
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line_number, line in enumerate(lines, start=1):
                # print(f"Processing line {line_number}: {line.strip()}")
                # print(f"Processing file: {file_path}")
                self.process_AWs(line, file_path, line_number, pattern)
                self.update_progress()
        self.save_unresolved_AWs()

    def preprocess_directory(self, directory_path):
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                self.process_file(file_path, self.pattern)
                self.update_progress()
        self.save_unresolved_AWs()

    def total_files(self, directory_path):
        count = 0
        for root, _, files in os.walk(directory_path):
            count += len(files)
        return count

        with dynamic_word_normalization1.progress:
            dynamic_word_normalization1.preprocess_directory(directory_path, pattern)
