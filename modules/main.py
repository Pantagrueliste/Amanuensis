import os
import sys
import logging

from config import Config
from unicode_replacement import UnicodeReplacement
from word_normalization import WordNormalization
from conflict_resolver import ConflictResolver
from rich.logging import RichHandler
from rich.progress import Progress

class Amanuensis:
    def __init__(self):
        self.config = Config()
        self.config.validate_paths()
        self.unicode_replacement = UnicodeReplacement(self.config)
        self.word_normalization = WordNormalization(self.config)
        self.conflict_resolver = ConflictResolver(self.config)

    def run(self):
        """
        Main method to start word normalization process.
        """
        if self.config.get('unicode_replacements', 'replacements_on'):
            self.run_unicode_replacement()

        print("Resolving conflicts between Machine and User Solutions...")
        self.conflict_resolver.detect_and_resolve_conflicts()
        print("Conflict Resolution Complete.")

        input_directory = self.config.get('paths', 'input_path')
        self.run_word_normalization()

    def run_unicode_replacement(self):
        """
        Perform Unicode replacements on all text files in the input directory.
        """
        print("Starting Unicode Replacement...")
        input_path = self.config.get('paths', 'input_path')
        file_paths = self.get_all_text_files(input_path)

        self.unicode_replacement.process_files(file_paths)
        self.unicode_replacement.save_log()
        print("Unicode Replacement Complete.")

    def run_word_normalization(self):
       """
       Perform Dynamic Word Normalization on all text files in the input directory.
       """
       print("Starting Dynamic Word Normalization...")
       input_directory = self.config.get('paths', 'input_path')
       self.word_normalization.preprocess_directory(input_directory)
       print("Dynamic Word Normalization Complete.")


    def get_all_text_files(self, dir_path):
        """
        Get all text files in the specified directory and its subdirectories.
        """
        text_files = []
        for subdir, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.txt'):
                    text_files.append(os.path.join(subdir, file))
        return text_files

if __name__ == '__main__':
    try:
        amanuensis = Amanuensis()
        amanuensis.run()
    except KeyboardInterrupt:
        print("\nQuitting the app.")
        sys.exit(0)
