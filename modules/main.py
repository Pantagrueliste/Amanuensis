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

from config import Config
from unicode_replacement import UnicodeReplacement
from dynamic_word_normalization1 import DynamicWordNormalization1
from conflict_resolver import ConflictResolver
from rich.logging import RichHandler
from rich.progress import Progress

nltk.download('wordnet')

class Amanuensis:
    def __init__(self):
        self.config = Config()
        self.config.validate_paths()
        self.unicode_replacement = UnicodeReplacement(self.config)
        self.word_normalization = DynamicWordNormalization1(self.config)
        self.conflict_resolver = ConflictResolver(self.config)

    def run(self):
        """
        Main method to start word normalization process.
        """
        if self.config.get('unicode_replacements', 'replacements_on'):
            self.run_unicode_replacement()

        input_directory = self.config.get('paths', 'input_path')
        self.run_word_normalization()

        print("Resolving conflicts between Machine and User Solutions...")
        self.conflict_resolver.detect_and_resolve_conflicts()
        print("Conflict Resolution Complete.")


    def run_unicode_replacement(self):
        """
        Perform Unicode replacements on all text files in the input directory.
        """
        print("Starting Unicode Replacement...")
        input_path = self.config.get('paths', 'input_path')
        file_paths = self.get_all_text_files(input_path)

        print("Launch process_files.")
        self.unicode_replacement.process_files(file_paths)
        print("process_files done.")
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
