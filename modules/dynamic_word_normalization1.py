import os
import json
import re
import orjson

from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from rich.progress import Progress
from atomic_update import atomic_write_json
from concurrent.futures import ProcessPoolExecutor
from threading import Lock
from logging_config import get_logger

lemmatizer = None
logger = get_logger(__name__)


def initialize_process():
    global lemmatizer, logger
    lemmatizer = WordNetLemmatizer()
    logger = get_logger(__name__)


def load_json(filepath):
    with open(filepath, 'rb') as file:
        return orjson.loads(file.read())


def save_json_data(pending_json_data):
    """
    Save pending json data to json disk.
    """
    for filename, data in pending_json_data.items():
        correct_path = os.path.join('data/', filename)
        atomic_write_json(data, correct_path)
    logger.info("Saved pending json data to disk.")


def save_json(file_path, data):
    atomic_write_json(data, file_path)


def consult_wordnet(aw):
    """
    Consults WordNet to find a solution for the abbreviated word
    """
    word_n = aw.replace("$", "n")
    if wordnet.synsets(word_n):
        return word_n
    word_m = aw.replace("$", "m")
    if wordnet.synsets(word_m):
        return word_m
    return None


def process_file_wrapper(args):
    return process_file(*args)


def process_aws(token, filename, token_idx, text, tokens, machine_solutions, user_solutions, machine_solutions_path, context_size):
    local_unresolved_aws = []
    if "$" not in token:
        return local_unresolved_aws

    start_index = max(0, token_idx - context_size)
    end_index = min(len(tokens), token_idx + context_size + 1)
    context_tokens = tokens[start_index:end_index]
    line_number = text.count('\n', 0, text.find(token)) + 1

    try:
        solution = machine_solutions.get(token)
        if not solution:
            solution = user_solutions.get(token)

        if not solution:
            try:
                solution = consult_wordnet(token)
            except Exception as e:
                logger.error(f"Error consulting WordNet for aw '{token}': {e}")
                solution = None

            if solution:
                machine_solutions[token] = solution
                save_json(machine_solutions_path, machine_solutions)
            else:
                #logger.debug(
                #    f"Processing token: {token} from file: {filename} at line number: {text.count('n', 0, text.find(token)) + 1}")
                log_unresolved_aw(token, filename, line_number, context_tokens, context_size, local_unresolved_aws)
    except Exception as e:
        logger.error(f"Error processing aws in file {filename} on line {line_number}: {e}")
    return local_unresolved_aws


def log_unresolved_aw(aw, filename, line_number, context_words, context_size, local_unresolved_aws):
    """
    Logs the unresolved aws to a json file.
    """
    aw_index = context_words.index(aw)
    start_index = max(0, aw_index - context_size)
    end_index = min(len(context_words), aw_index + context_size + 1)
    context = " ".join(context_words[start_index:end_index])
    sanitized_aw = re.sub(r"[,;:!?(){}]", "", aw)
    local_unresolved_aws.append(
        {
            "filename": filename,
            "line": line_number,
            "column": aw_index,
            "unresolved_aw": sanitized_aw,
            "context": context,
        }
    )
    # logger.debug(f"Logging unresolved word: {sanitized_aw} from file: {filename} at line number: {line_number}")


def process_file(file_path, machine_solutions, user_solutions, context_size, machine_solutions_path):
    local_unresolved_aws = []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
            tokens = text.split()
            for token_idx, token in enumerate(tokens):
                unresolved_for_token = process_aws(token, file_path, token_idx, text, tokens, machine_solutions,
                                                   user_solutions, machine_solutions_path, context_size)
                local_unresolved_aws.extend(unresolved_for_token)
    except UnicodeDecodeError:
        logger.error(f"Error decoding file {file_path} as UTF-8.")

    return local_unresolved_aws

class DynamicWordNormalization1:
    def __init__(self, config):
        self.config = config
        self.pattern = r"\w*\$\w*"
        self.lemmatizer = WordNetLemmatizer()
        self.user_solutions_path = self.config.get("data", "user_solution_path")
        self.user_solutions = load_json(self.user_solutions_path) or {}
        self.machine_solutions_path = self.config.machine_solution_path
        self._machine_solutions = None
        self.unresolved_aws_path = self.config.unresolved_aw_path
        self.unresolved_aws_log = []
        data_directory = os.path.dirname(self.machine_solutions_path)
        if not os.path.exists(data_directory):
            os.makedirs(data_directory)

        self.load_machine_solutions()
        self.context_size = int(config.get("settings", "context_size"))
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

    def load_machine_solutions(self):
        try:
            with open(self.machine_solutions_path, "r", encoding="utf-8") as file:
                contents = file.read().strip()
                self.machine_solutions = json.loads(contents) if contents else {}
        except FileNotFoundError:
            logger.error("Machine solutions file not found.")
            self.machine_solutions = {}

    def extract_aws(self, text):
        self.compiled_pattern.findall(text)

<<<<<<< HEAD
    @staticmethod
    def total_files(directory_path):
        count = 0
        for root, _, files in os.walk(directory_path):
            count += len(files)
        return count
=======
    def save_json(self, file_path, data):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


    def extract_AWs(self, text):
        pattern = r'\w*\$\w*'
        print(f"From text: {text.strip()}")
        return re.findall(pattern, text)


    def process_AWs(self, text, filename, line_number):
        pattern = r'\w*\$\w*|\w+'
        words = re.findall(pattern, text)
        AWs = [word for word in words if '$' in word]
        context_size = self.config.get('settings', 'context_size')
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
                    self.log_unresolved_AW(AW, filename, line_number, context_words, context_size)


    def consult_wordnet(self, AW):
        print(f"Consulting WordNet for {AW}...")
        word_n = AW.replace('$', 'n')
        if wordnet.synsets(word_n):
            print(f"Found solution: {word_n}")
            return word_n
        word_m = AW.replace('$', 'm')
        if wordnet.synsets(word_m):
            print(f"Found solution: {word_m}")
            return word_m
        return None


    def log_unresolved_AW(self, AW, filename, line_number, context_words, context_size):
        print(f"Logging unresolved AW: {AW}")
        AW_index = context_words.index(AW)
        start_index = max(0, AW_index - self.context_size)
        end_index = min(len(context_words) - 1, AW_index + self.context_size)
        context = ' '.join(context_words[start_index:end_index + 1])
        self.unresolved_AWs_log.append({
            'filename': filename,
            'line': line_number,
            'column': AW_index,
            'unresolved_AW': AW,
            'context': context
        })


    def save_unresolved_AWs(self):
        unresolved_AWs_path = 'data/unresolved_AW.json'
        self.save_json(unresolved_AWs_path, self.unresolved_AWs_log)


    def process_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line_number, line in enumerate(lines, start=1):
                #print(f"Processing line {line_number}: {line.strip()}")
                #print(f"Processing file: {file_path}")
                self.process_AWs(line, file_path, line_number)
        self.save_unresolved_AWs()
>>>>>>> 75d7fc8 (DWN1.1 completion)

    def save_unresolved_aws(self):
        logger.info(f"Saving {len(self.unresolved_aws_log)} unresolved aws.")
        unresolved_aws_path = self.config.get("data", "unresolved_aws_path")
        save_json(unresolved_aws_path, self.unresolved_aws_log)
        # logger.debug(
        #     f"Attempting to save {len(self.unresolved_aws_log)} unresolved words to {self.config.get('data', 'unresolved_aws_path')}")

    def preprocess_directory(self, directory_path):
<<<<<<< HEAD
        logger.setLevel(50)
        total_files = DynamicWordNormalization1.total_files(directory_path)

        with ProcessPoolExecutor(initializer=initialize_process) as executor, Progress() as progress:
            task = progress.add_task("[cyan]Analyzing files...", total=total_files)
            file_args = []

            for root, _, files in os.walk(directory_path):
                for file_name in files:
                    if not file_name.startswith('.') and file_name.endswith('.txt'):
                        file_path = os.path.join(root, file_name)
                        args = (file_path, self.machine_solutions, self.user_solutions, int(self.context_size),
                                self.machine_solutions_path)
                        assert len(args) == 5
                        file_args.append(args)

            aggregated_unresolved_aws = []

            results = executor.map(process_file_wrapper, file_args)

            for local_unresolved in results:
                aggregated_unresolved_aws.extend(local_unresolved)
                progress.update(task, advance=1)

            self.unresolved_aws_log = aggregated_unresolved_aws
            self.save_unresolved_aws()
=======
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                self.process_file(file_path)
        self.save_unresolved_AWs()
>>>>>>> 75d7fc8 (DWN1.1 completion)
