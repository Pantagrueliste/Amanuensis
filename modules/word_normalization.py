import os
import json
import string
import logging
from time import time
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from config import Config

class WordNormalization:

    def __init__(self, config):
        self.config = config
        self.lemmatizer = WordNetLemmatizer()
        self.user_solutions_path = 'data/user_solution.json'
        self.machine_solutions_path = 'data/machine_solution.json'
        self.load_user_solutions()
        self.load_machine_solutions()
        self.setup_logging()

    def load_user_solutions(self):
        """
        Load user solutions from a JSON file or create it if it doesn't exist.
        """
        try:
            with open(self.user_solutions_path, 'r', encoding='utf-8') as file:
                self.user_solutions = json.load(file)
        except FileNotFoundError:
            self.user_solutions = {}
            self.save_json(self.user_solutions_path, self.user_solutions)

    def load_machine_solutions(self):
        """
        Load machine solutions from a JSON file or create it if it doesn't exist.
        """
        try:
            with open(self.machine_solutions_path, 'r', encoding='utf-8') as file:
                self.machine_solutions = json.load(file)
        except FileNotFoundError:
            self.machine_solutions = {}
            self.save_json(self.machine_solutions_path, self.machine_solutions)

    def save_json(self, path, data):
        """
        Save a dictionary to a JSON file.
        """
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def setup_logging(self):
        """
        Set up logging based on configuration settings.
        """
        log_file_path = 'logs/dynamic_word_normalization.json'
        logging.basicConfig(filename=log_file_path, level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')

    def log_change(self, file_path, line_num, original, replacement):
        """
        Log a replacement to the log file.
        """
        log_entry = {
            'timestamp': time(),
            'file_name': os.path.basename(file_path),
            'line_number': line_num,
            'original': original,
            'replacement': replacement
        }
        logging.info(json.dumps(log_entry))

    def normalize_word(self, word):
        """
        Normalize a word based on user solutions, machine solutions, and WordNet.
        """
        word_wo_punctuation, trailing_punctuation = self.remove_punctuation(word)

        # Check User Solutions
        if word_wo_punctuation in self.user_solutions:
            return self.user_solutions[word_wo_punctuation] + trailing_punctuation

        # Check Machine Solutions
        if word_wo_punctuation in self.machine_solutions:
            return self.machine_solutions[word_wo_punctuation] + trailing_punctuation

        # Attempt to resolve using WordNet
        lemma = self.lemmatizer.lemmatize(word_wo_punctuation)
        if wordnet.synsets(lemma):
            self.machine_solutions[word_wo_punctuation] = lemma
            self.save_json(self.machine_solutions_path, self.machine_solutions)
            return lemma + trailing_punctuation

        # If unresolved, ask the user
        correct_word = input(f"Please enter the full replacement for '{word_wo_punctuation}' or press Enter to keep original: ")
        if correct_word:
            self.user_solutions[word_wo_punctuation] = correct_word
            self.save_json(self.user_solutions_path, self.user_solutions)
            return correct_word + trailing_punctuation

        return word

    def remove_punctuation(self, word):
        """
        Remove punctuation from a word and return the word and trailing punctuation separately.
        """
        word_wo_punctuation = word.rstrip(string.punctuation)
        trailing_punctuation = word[len(word_wo_punctuation):]
        return word_wo_punctuation, trailing_punctuation

    def normalize_text(self, text):
        """
        Normalize the text by normalizing each word.
        """
        words = text.split()
        normalized_words = [self.normalize_word(word) for word in words]
        return ' '.join(normalized_words)

    def process_file(self, input_file_path):
        """
        Read a file, normalize its content, and save it to a new file.

        Parameters:
        - input_file_path (str): The path of the file to be processed.
        """
        # Read the content of the file
        with open(input_file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()

        # Normalize each line of the file
        normalized_content = []
        for line_num, line in enumerate(content, 1):
            normalized_line = self.normalize_text(line)
            normalized_content.append(normalized_line)

            # Log the changes for each word in the line
            original_words = line.split()
            normalized_words = normalized_line.split()
            for orig, norm in zip(original_words, normalized_words):
                if orig != norm:
                    self.log_change(input_file_path, line_num, orig, norm)

        # Save the normalized content to a new file
        output_file_path = os.path.join(self.config.get('paths', 'output_path'), os.path.basename(input_file_path))
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.writelines(normalized_content)

    def preprocess_directory(self, input_directory):
        """
        Pre-process all files in a directory and its subdirectories.
        """
        # Recursively process files in the directory and its subdirectories
        for dirpath, _, filenames in os.walk(input_directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                self.process_file(file_path)
                # Here you can add a progress update, e.g. printing the filename

    def run(self):
        """
        Main method to start word normalization process.
        """
        input_directory = self.config.get('paths', 'input_path')
        self.preprocess_directory(input_directory)
