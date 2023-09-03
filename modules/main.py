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
import nltk
import signal
import json
import logging

from config import Config
from unicode_replacement import UnicodeReplacement
from dynamic_word_normalization1 import DynamicWordNormalization1
from dynamic_word_normalization2 import DynamicWordNormalization2
from dynamic_word_normalization3 import DynamicWordNormalization3
from atomic_update import atomic_write_json
from conflict_resolver import ConflictResolver
from multiprocessing.pool import IMapUnorderedIterator
from dynamic_word_normalization2 import UserQuitException
from rich.logging import RichHandler
from rich.progress import Progress
from art import text2art

nltk.download("wordnet")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(module)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("amanuensis.log", mode="a")
    ]
)

class MainApp:
    def __init__(self):
        self.ongoing_processes = []
        self.pending_json_data = {}
        self.config = Config()
        logging_level = self.config.get("settings", "logging_level")
        difficult_passages_json_path = self.config.get("data", "difficult_passages_path", "Amanuensis/data")
        from atomic_update import atomic_write_json

    def save_json_data(self):  ## connect to atomic_update.py
        """
        Save pending json data to json disk.
        """
        for filename, data in self.pending_json_data.items():
            atomic_write_json(filename, data)
        logging.info("Saved pending json data to disk.")

    def terminate_ongoing_processes(self):
        """
        Terminate all ongoing processes.
        """
        for process in self.ongoing_processes:
            process.terminate()
        logging.info("Terminated all ongoing processes.")

    def signal_handler(self, signal, frame):
        """
        Handle Ctrl+C signal.
        """
        logging.info("Ctrl+C pressed.")
        self.save_json_data()
        print("\n\nYou pressed Ctrl+C. Initiating shutdown...")
        self.terminate_ongoing_processes()
        logging.info("Cleanup complete. Exiting.")
        print("Au revoir!")
        sys.exit(0)


class Amanuensis:
    def __init__(self, main_app_instance, config):
        """
        Initialize Amanuensis.
        """
        print(text2art("Amanuensis"))
        self.main_app = main_app_instance
        self.config = config
        config.print_config_recap()
        self.config.validate_paths()
        self.unicode_replacement = UnicodeReplacement(self.config)
        self.word_normalization = DynamicWordNormalization1(self.config)
        self.ambiguous_AWs = self.config.get_ambiguous_AWs()
        self.word_normalization2 = DynamicWordNormalization2(
                    self.config, ambiguous_AWs=self.ambiguous_AWs
                )
        self.conflict_resolver = ConflictResolver(self.config)
        self.word_normalization3 = DynamicWordNormalization3(self.config)



    def run(self):
        """
        Execution sequence of Amanuenis.
        """
        # Unicode Replacement (optional)
        if self.config.get("unicode_replacements", "replacements_on"):
            print("Starting Unicode Replacement...")
            self.run_unicode_replacement()
            proceed = input(
                "Unicode Replacement is complete. Do you want to proceed to Dynamic Word Normalization? (y/n): "
            )
            if proceed.lower() != "y":
                print("Exiting.")
                logging.info("User exited after Unicode Replacement was complete.")
                self.main_app.save_json_data()
                self.main_app.terminate_ongoing_processes()
                sys.exit(0)

        # DWN1.1
        print("Starting DWN1.1...")
        self.run_word_normalization()
        # DWN1.2
        print("Starting DWN1.2...")
        self.word_normalization2.process_unresolved_AWs()
        # DWN2
        print("Starting DWN2...")
        #logging.info("Starting DWN2...")
        self.word_normalization3.analyze_difficult_passages()

        #input_directory = self.config.get("paths", "input_path")

        # Conflict Resolution
        proceed = input(
            "Dynamic Word Normalization is complete. Do you want to proceed to Conflict Resolution? (y/n): "
        )
        if proceed.lower() != "y":
            print("Exiting.")
            logging.info("User exited after Dynamic Word Normalization was complete.")
            self.main_app.save_json_data()
            self.main_app.terminate_ongoing_processes()
            sys.exit(0)

        print("Resolving conflicts between Machine and User Solutions...")
        logging.info("Resolving conflicts between Machine and User Solutions...")
        self.conflict_resolver.detect_and_resolve_conflicts()
        print("Conflict Resolution Complete.")
        logging.info("Conflict Resolution Complete.")

        proceed = input(
            "Conflict Resolution is complete. Do you want to proceed to processing all files? (y/n): "
        )
        if proceed.lower() != "y":
            print("Exiting.")
            logging.info("User exited after Conflict Resolution was complete.")
            self.main_app.save_json_data()
            self.main_app.terminate_ongoing_processes()
            sys.exit(0)

        difficult_passages_json_path = self.config.get("data", "difficult_passages")
        user_solution_json_path = self.config.get("data", "user_solution_path")
        input_path = self.config.get("paths", "input_path")
        output_path = self.config.get("paths", "output_path")

        # TODO files processing section


    def run_unicode_replacement(self):
        """
        Perform Unicode replacements on all text files in the input directory.
        """
        print("Starting Unicode Replacement...")
        logging.info("Starting Unicode Replacement...")
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
        logging.info("Starting Dynamic Word Normalization...")
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
    main_app_instance = MainApp()
    signal.signal(signal.SIGINT, lambda s, f: main_app_instance.signal_handler(s, f))
    try:
        amanuensis = Amanuensis(main_app_instance, main_app_instance.config)
        amanuensis.run()
    except UserQuitException:
        logging.info("User quit the application.")
        print("Exiting the application.")
        main_app_instance.save_json_data()
        main_app_instance.terminate_ongoing_processes()
        sys.exit(0)
