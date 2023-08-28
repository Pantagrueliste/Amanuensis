"""
Amanuensis is an application designed to accelerate the
large scale normalization of abbreviated early-modern texts.
It is composed of an optional Unicode Replacement module and
of a Dynamic Word Normalization module. The former applies
replacements and deletions of unicode characters in parallel,
while logging every single change on a json file. The latter
relies on the Wordnet dictionary, a user defined dictionary,
and on the optional suggestions of GPT-4, to solve all the
remaining edge cases.
"""

import os
import sys
import logging
import nltk
import signal
import json

from config import Config
from unicode_replacement import UnicodeReplacement
from dynamic_word_normalization1 import DynamicWordNormalization1
from dynamic_word_normalization2 import DynamicWordNormalization2
from conflict_resolver import ConflictResolver
from multiprocessing.pool import IMapUnorderedIterator
from dynamic_word_normalization2 import UserQuitException
from rich.logging import RichHandler
from rich.progress import Progress
from art import text2art

nltk.download("wordnet")

ongoing_processes = []
pending_json_data = {}

def save_json_data():
    """
    Save pending json data to json disk.
    """
    for filename, data in pending_json_data.items():
        with open(filename, "w") as f:
            json.dump(data, f)
    logging.info("Saved pending json data to disk.")

def terminate_ongoing_processes():
    """
    Terminate all ongoing processes.
    """
    for process in ongoing_processes:
        process.terminate()
    logging.info("Terminated all ongoing processes.")

def signal_handler(signal, frame):
    """
    Handle Ctrl+C signal.
    """
    logging.info("Ctrl+C pressed.")
    save_json_data()
    print("\n\nYou pressed Ctrl+C. Initiating shutdown...")
    terminate_ongoing_processes()
    logging.info("Cleanup complete. Exiting.")
    print("Au revoir!")
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

class Amanuensis:
    def __init__(self):
        """
        Initialize Amanuensis.
        """
        print(text2art("Amanuensis"))
        self.config = Config()
        self.config.validate_paths()
        self.unicode_replacement = UnicodeReplacement(self.config)
        self.word_normalization = DynamicWordNormalization1(self.config)
        self.ambiguous_AWs = self.config.get_ambiguous_AWs()
        self.word_normalization2 = DynamicWordNormalization2(ambiguous_AWs=self.ambiguous_AWs)
        self.conflict_resolver = ConflictResolver(self.config)


    def run(self):
        """
        Main method to start word normalization process.
        """
        if self.config.get("unicode_replacements", "replacements_on"):
            self.run_unicode_replacement()
            proceed = input("Unicode Replacement is complete. Do you want to proceed to Dynamic Word Normalization? (y/n): ")
            if proceed.lower() != 'y':
                print("Exiting.")
                save_json_data()
                terminate_ongoing_processes()
                sys.exit(0)

        input_directory = self.config.get("paths", "input_path")
        self.run_word_normalization()
        self.word_normalization2.process_unresolved_AWs()

        proceed = input("Dynamic Word Normalization is complete. Do you want to proceed to Conflict Resolution? (y/n): ")
        if proceed.lower() != 'y':
            print("Exiting.")
            save_json_data()
            terminate_ongoing_processes()
            sys.exit(0)

        print("Resolving conflicts between Machine and User Solutions...")
        self.conflict_resolver.detect_and_resolve_conflicts()
        print("Conflict Resolution Complete.")

    def run_unicode_replacement(self):
        """
        Perform Unicode replacements on all text files in the input directory.
        """
        print("Starting Unicode Replacement...")
        input_path = self.config.get("paths", "input_path")
        file_paths = self.get_all_text_files(input_path)

        # print("Launch process_files.")
        self.unicode_replacement.process_files(file_paths)
        # print("process_files done.")
        self.unicode_replacement.save_log()


    def run_word_normalization(self):
        """
        Perform Dynamic Word Normalization on all text files in the input directory.
        """
        print("Starting Dynamic Word Normalization...")
        input_directory = self.config.get("paths", "input_path")

        self.word_normalization.preprocess_directory(input_directory)


    def get_all_text_files(self, dir_path):
        """
        Get all text files in the specified directory and its subdirectories.
        """
        text_files = []
        for subdir, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".txt"):
                    text_files.append(os.path.join(subdir, file))
        return text_files

if __name__ == "__main__":
    try:
        amanuensis = Amanuensis()
        amanuensis.run()
    except UserQuitException:
        print("Exiting the application.")
        save_json_data()
        terminate_ongoing_processes()
        sys.exit(0)
