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
import signal
import sys
from typing import Any

from art import text2art

from atomic_update import atomic_write_json
from config import Config
from conflict_resolver import ConflictResolver
from dynamic_word_normalization1 import DynamicWordNormalization1
from dynamic_word_normalization2 import DynamicWordNormalization2
from dynamic_word_normalization2 import UserQuitException
from dynamic_word_normalization3 import DynamicWordNormalization3
from logging_config import get_logger
from unicode_replacement import UnicodeReplacement
from file_processor import FileProcessor


class MainApp:
    pending_json_data: dict[Any, Any]

    def __init__(self):
        self.logger = get_logger(__name__)
        self.ongoing_processes = []
        self.pending_json_data = {}
        self.config = Config()
        self.config.get("settings", "logging_level")

    def save_json_data(self):
        """
        Save pending json data to json disk.
        """
        for filename, data in self.pending_json_data.items():
            atomic_write_json(filename, data)
        self.logger.info("Saved pending json data to disk.")

    def terminate_ongoing_processes(self):
        """
        Terminate all ongoing processes.
        """
        for process in self.ongoing_processes:
            process.terminate()
        self.logger.info("Terminated all ongoing processes.")

    def signal_handler(self):
        """
        Handle Ctrl+C signal.
        """
        self.logger.info("Ctrl+C pressed.")
        self.save_json_data()
        print("\n\nYou pressed Ctrl+C. Initiating shutdown...")
        self.terminate_ongoing_processes()
        self.logger.info("Cleanup complete. Exiting.")
        print("Au revoir!")
        sys.exit(0)


class Amanuensis:
    def __init__(self, main_app_instance, config):
        """
        Initialize Amanuensis.
        """
        self.logger = get_logger(__name__)
        print(text2art("Amanuensis"))
        self.main_app = main_app_instance
        self.config = config
        config.print_config_recap()
        self.config.validate_paths()
        self.unicode_replacement = UnicodeReplacement(self.config)
        self._word_normalization = DynamicWordNormalization1(self.config)
        self.ambiguous_aws = self.config.get_ambiguous_aws()
        self.word_normalization2 = DynamicWordNormalization2(
                    self.config, ambiguous_aws=self.ambiguous_aws
                )
        self.conflict_resolver = ConflictResolver(self.config)
        self.word_normalization3 = DynamicWordNormalization3(self.config)

    @property
    def word_normalization(self):
        if not hasattr(self, "_word_normalization"):
            self._word_normalization = DynamicWordNormalization1(self.config)
        return self._word_normalization

    def run(self):
        """
        Execution sequence of Amanuenis.
        """
        if self.config.get("unicode_replacements", "replacements_on"):
            self.run_unicode_replacement()
            proceed = input(
                "Unicode Replacement is complete. Do you want to proceed to Dynamic Word Normalization? (y/n): "
            )
            if proceed.lower() != "y":
                print("Exiting.")
                self.logger.info("User exited after Unicode Replacement was complete.")
                self.main_app.save_json_data()
                self.main_app.terminate_ongoing_processes()
                sys.exit(0)

        # DWN1.1
        self.logger.info("Starting Dynamic Word Normalization Phase 1.1...")
        self.run_word_normalization()
        # DWN1.2
        self.logger.info("Starting Dynamic Word Normalization Phase 1.2...")
        unresolved_path = self.config.get("data", "unresolved_aws_path")
        self.word_normalization2.process_unresolved_aws(unresolved_path)
        # DWN2
        self.logger.info("Starting Dynamic Word Normalization Phase 2...")
        self.word_normalization3.analyze_difficult_passages()

        # Conflict Resolution
        proceed = input(
            "Dynamic Word Normalization is complete. Do you want to proceed to Conflict Resolution? (y/n): "
        )
        if proceed.lower() != "y":
            print("Exiting.")
            self.logger.info("User exited after Dynamic Word Normalization was complete.")
            self.main_app.save_json_data()
            self.main_app.terminate_ongoing_processes()
            sys.exit(0)

        self.logger.info("Resolving conflicts between Machine and User Solutions...")
        self.conflict_resolver.detect_and_resolve_conflicts()
        self.logger.info("Conflict Resolution Complete.")

        if proceed.lower() != "y":
            print("Exiting.")
            self.logger.info("User exited after Conflict Resolution was complete.")
            self.main_app.save_json_data()
            self.main_app.terminate_ongoing_processes()
            sys.exit(0)

        self.logger.info("Starting file processing...")
        processor = FileProcessor(config_file='config.toml',
                                      user_solution_file=os.path.join(self.config.get('paths', 'output_path'),
                                                                      'data/user_solution.json'),
                                      machine_solution_file=os.path.join(self.config.get('paths', 'output_path'),
                                                                         'data/machine_solution.json'))
        processor.run()
        self.logger.info("File processing complete.")

    def run_unicode_replacement(self):
        """
        Perform Unicode replacements on all text files in the input directory.
        """
        self.logger.info("Starting Unicode Replacement...")
        input_path = self.config.get("paths", "input_path")
        file_paths = Amanuensis.get_all_text_files(input_path)

        # print("Launch process_files.")
        self.unicode_replacement.process_files(file_paths)
        # print("process_files done.")
        self.unicode_replacement.save_log()

    def run_word_normalization(self):
        """
        Perform Dynamic Word Normalization on all text files in the input directory.
        """
        # self.logger.info("run_word_normalization...")
        input_directory = self.config.get("paths", "input_path")

        self.word_normalization.preprocess_directory(input_directory)

    @staticmethod
    def get_all_text_files(dir_path):
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
    logger = get_logger(__name__)
    main_app_instance = MainApp()
    signal.signal(signal.SIGINT, lambda s, f: main_app_instance.signal_handler())
    try:
        amanuensis = Amanuensis(main_app_instance, main_app_instance.config)
        amanuensis.run()
    except UserQuitException:
        logger.info("User quit the application.")
        print("Exiting the application.")
        main_app_instance.save_json_data()
        main_app_instance.terminate_ongoing_processes()
        sys.exit(0)
