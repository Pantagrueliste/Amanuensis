"""
This module normalizes early modern texts, by systematically replacing specific characters
and by offering ad hoc solutions using a wordnet and a user-defined dictionaries.
"""

import os
import json
import sys
import csv
import string
import datetime
import toml
import logging

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import Levenshtein
from art import text2art
from colorama import init, Fore, Back, Style
from tqdm import tqdm
from toml.decoder import TomlDecodeError

# Title
print(text2art("Amanuensis"))

# Initialize colorama for colored console output
init(autoreset=True)

# Download wordnet corpus, used for word normalization
nltk.download('wordnet')

# Create a WordNetLemmatizer object, used for word normalization
lemmatizer = WordNetLemmatizer()

# Load user solutions from a JSON file. These are preferred solutions for word normalization.
try:
    with open('user_solutions.json', 'r', encoding='utf-8') as file:
        user_solutions = json.load(file)
except FileNotFoundError:
    user_solutions = {}

# Initialize logging
logging.basicConfig(filename='normalization.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# This function saves a difficult passage to a CSV file. It appends a row containing the file path,
# line number, and context of the difficult passage.
def log_difficult_passage(file_path,
    line_number,
    context,
    csv_file='difficult_passages.csv'):
    """
    This function saves a difficult passage to a CSV file.
    It appends a row containing the file path, line number, and context of the difficult passage.
    """
    with open(csv_file, mode='a', newline='', encoding='utf-8') as csv_file_obj:
        writer = csv.writer(csv_file_obj)
        writer.writerow([file_path, line_number, context])

def check_user_solutions(word_wo_punctuation, user_solutions):
    if word_wo_punctuation in user_solutions and word_wo_punctuation not in ["the$"]:
        return user_solutions[word_wo_punctuation]
    return None

def check_unicode_replacement(word_wo_punctuation, unicode_replacements):
    if word_wo_punctuation in unicode_replacements:
        return unicode_replacements[word_wo_punctuation]
    return None

def get_synsets_replacement(word_wo_punctuation, trailing_punctuation, lemmatizer):
    """
    This function gets the synsets replacements for the given word.

    Parameters:
    word_wo_punctuation (str): The word without punctuation.
    trailing_punctuation (str): The trailing punctuation.
    lemmatizer (WordNetLemmatizer): The lemmatizer object.

    Returns:
    str: The synsets replacement if found, else None.
    """
    modified_word_n = word_wo_punctuation.replace('$', 'n')
    n_in_dict = wordnet.synsets(lemmatizer.lemmatize(modified_word_n))

    modified_word_m = word_wo_punctuation.replace('$', 'm')
    m_in_dict = wordnet.synsets(lemmatizer.lemmatize(modified_word_m))

    if n_in_dict:
        return modified_word_n + trailing_punctuation
    elif m_in_dict:
        return modified_word_m + trailing_punctuation
    return None

def remove_punctuation(word):
    """
    This function removes punctuation from a given word.
    """
    word_wo_punctuation = word.rstrip(string.punctuation)
    trailing_punctuation = word[len(word_wo_punctuation):]
    return word_wo_punctuation, trailing_punctuation

def normalize_word(word,
                 file_name,
                 line_number,
                 line_words,
                 word_index,
                 replacement_log,
                 context_size):
    """
    This function normalizes a given word and logs the replacements made.
    """
    global json_solutions_counter
    word_wo_punctuation, trailing_punctuation = remove_punctuation(word)

    user_solution = check_user_solutions(word_wo_punctuation, user_solutions)
    if user_solution is not None:
        logging.info(f"{Fore.GREEN}{file_name}, line {line_number}: '{word}' replaced with '{user_solution}' using a previous user solution")
        json_solutions_counter += 1
        return user_solution + trailing_punctuation

    unicode_replacement = check_unicode_replacement(word_wo_punctuation, unicode_replacements)
    if unicode_replacement is not None:
        logging.info(f"In the file '{file_name}' at line {line_number}, "
              f"found a solution in the user_solutions file for the word '{word}'.")
        json_solutions_counter += 1
        return unicode_replacement + trailing_punctuation

    if '$' not in word_wo_punctuation:
        return word_wo_punctuation + trailing_punctuation

    synsets_replacement = get_synsets_replacement(word_wo_punctuation, trailing_punctuation, lemmatizer)
    if synsets_replacement is not None:
        if word_wo_punctuation not in user_solutions:
            message1 = f"The original word was '{Fore.RED + word + Style.RESET_ALL}'"
            message2 = f"in file '{file_name}' at line {line_number}. After replacing $, '{Fore.GREEN + synsets_replacement + Style.RESET_ALL}'"
            message3 = "is in the dictionary, saving as such."
            logging.info(f"{Fore.LIGHTBLACK_EX}{message1}{Style.RESET_ALL}"
                         f"{Fore.LIGHTBLACK_EX}{message2}{Style.RESET_ALL}"
                         f"{Fore.LIGHTBLACK_EX}{message3}{Style.RESET_ALL}")
            return synsets_replacement
        else:
            return user_solutions[word_wo_punctuation] + trailing_punctuation

    else:
        message1 = (
            f"Could not find a match for "
            f"'{Fore.RED + word_wo_punctuation + Style.RESET_ALL}'"
        )
        message2 = (
            f"in the dictionary after trying both replacements. "
            f"Found in file "
            f"'{file_name}' at line {line_number}."
        )

        print(Fore.LIGHTBLACK_EX + message1 + Style.RESET_ALL +
              Fore.LIGHTBLACK_EX + message2 + Style.RESET_ALL)
        context_words = (line_words[max(0, word_index - 4):word_index] +
                         ['<...>'] +
                         line_words[word_index+1:min(len(line_words), word_index + 5)])
        print("Context: ", ' '.join(context_words))

        while True:
            correct_word_prompt = (
                Fore.LIGHTBLACK_EX
                + f"Please enter 'n' or 'm' to replace $, or enter "
                + f"the full replacement for "
                + f"'{Fore.RED + word_wo_punctuation + Style.RESET_ALL}', "
                + "or type 'quit' to exit the script, or '`' if you don't know: "
            )
            correct_word = input(correct_word_prompt)

            if correct_word.lower() == 'quit':
                os.system('cls' if os.name == 'nt' else 'clear')
                print("Exiting the script...")
                sys.exit()

            elif correct_word == '`':
                start_index = max(0, word_index - context_size)
                end_index = min(len(line_words), word_index + context_size)
                context_before = line_words[start_index:word_index]
                context_after = line_words[word_index + 1:end_index]
                context_words = context_before + ['<...>'] + context_after
                log_difficult_passage(file_name, line_number, ' '.join(context_words))
                print("Difficult passage logged. Please continue with the next word.")

                user_solutions[word_wo_punctuation] = word_wo_punctuation
                with open('user_solutions.json', 'w', encoding='utf-8') as json_file:
                    json.dump(user_solutions, json_file)

                return word

            elif correct_word.lower() == 'n':
                correct_word = word_wo_punctuation.replace('$', 'n')

            elif correct_word.lower() == 'm':
                correct_word = word_wo_punctuation.replace('$', 'm')

            lev_distance = Levenshtein.distance(word_wo_punctuation.replace('$', ''), correct_word)

            if lev_distance > word_wo_punctuation.count('$') + 1:
                print(Fore.YELLOW +
                      "Your input seems significantly different from the original word. "
                      "Please confirm if this is correct.")
                confirmation = input("Type 'yes' to confirm, 'no' to input again: ").lower()
                while confirmation not in ['yes', 'no']:
                    confirmation = input(Fore.RED +
                                         "Invalid response. Type 'yes' to confirm, 'no' to input again: ").lower()
                if confirmation == 'no':
                    continue
            break

        json_solutions_counter += 1
        logging.info(f"In the file '{file_name}' at line {line_number}, "
              f"found a solution in the user_solutions file for the word '{word}'.")
        if word_wo_punctuation != "the$":
            user_solutions[word_wo_punctuation] = correct_word
        with open('user_solutions.json', 'w', encoding='utf-8') as file:
            json.dump(user_solutions, file)

        return correct_word + trailing_punctuation

    return word


def process_file(file_path,
                final_dir,
                replacement_log,
                context_size):
    """Processes a file, normalizes its words and saves the result in a new file."""
    replacement_count = 0

    with open(file_path, 'r', encoding='utf-8') as input_file:
        lines = input_file.read().split('\n')

    def has_special_char(word):
        special_chars = "\u00B6\u261E\u2740\u2767Ʋ&c."
        return any(char in word for char in special_chars)

    for line_number, line in enumerate(lines, start=1):
        words_in_line = line.split()
        normalized_words = []
        for i, word in enumerate(words_in_line):
            norm_word = normalize_word(word, file_path, line_number,
                                    words_in_line, i, replacement_log, context_size)
            normalized_words.append(norm_word)
        replacement_count += sum(1 for word in words_in_line if has_special_char(word))
        lines[line_number-1] = ' '.join(normalized_words)

    new_file_path = os.path.join(final_dir, os.path.relpath(file_path))
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(lines))

    logging.info(f"A total of {replacement_count} replacements were made in the file '{file_path}'")
    return replacement_count, 1

class ProgressBar:
    """ class that handles progress bar display."""
    def __init__(self, total, description="Processing"):
        self.total = total
        self.description = description
        self.bar = tqdm(total=self.total, desc=self.description)

    def update(self, n=1):
        self.bar.update(n)

    def close(self):
        self.bar.close()

def load_config():
    """ function to get the logging level from the config file."""
    try:
        config_values = toml.load("config.toml")
    except FileNotFoundError:
        logging.error("Config file not found. Using default settings.")
        config_values = {"directories": {"working_directory": "./"},
                "logging": {"level": "verbose"},
                "settings": {"context_size": 5}
                }
    except TomlDecodeError as e:
        logging.error(f"Error while parsing config file: {str(e)}. Using default settings.")
        config_values = {"directories": {"working_directory": "./"},
                "logging": {"level": "verbose"},
                "settings": {"context_size": 5}
                }
    return config_values

def configure_logging(logging_level):
    """ function that sets up logging based on the logging level."""
    numeric_level = {"minimal": logging.WARNING, "verbose": logging.INFO,
                     "statistic": logging.ERROR}.get(logging_level.lower(), logging.INFO)
    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

def main(target_directory, text_context_size, unicode_replacements):
    """Main function to normalize all text files in a directory."""
    print("\nStarting normalization...\n")

    # Calculate total_files in a more readable way
    total_files = 0
    for _, _, files in os.walk(target_directory):
        for file in files:
            if file.endswith('.txt'):
                total_files += 1

    # Initialize progress bar
    bar = ProgressBar(total_files, "Files Processed")

    final_dir = os.path.join(target_directory, "FinalText")
    file_counter = 0
    total_replacements = 0
    total_files = 0
    global json_solutions_counter
    json_solutions_counter = 0
    total_processed_files = 0
    start_time = datetime.datetime.now()

    with open('replacement_log.txt', 'w', encoding='utf-8') as replacement_log:
        for subdir, dirs, files in os.walk(target_directory):
            total_files += len(
                [f for f in files if f.endswith('.txt')]
            )  # count only txt files
            for file in files:
                if file.endswith('.txt'):
                    replacements, processed_files = process_file(
                        os.path.join(subdir, file), final_dir, replacement_log, text_context_size
                    )
                    total_processed_files += processed_files
                    total_replacements += replacements
                    percent_complete = (
                        total_processed_files / total_files
                    ) * 100
                    elapsed_time = datetime.datetime.now() - start_time
                    proportion = (
                        json_solutions_counter / total_replacements
                    ) * 100 if total_replacements != 0 else 0
                    estimated_remaining = (
                        (
                            (elapsed_time / total_processed_files) *
                            (total_files - total_processed_files)
                        ).total_seconds()
                    )
                    logging.info(
                        f"\nStats after file {total_processed_files}:"
                        f"\nNumber of files normalized: {total_processed_files}"
                        f"\nTotal replacements made: {total_replacements}"
                        f"\nElapsed time: {elapsed_time}"
                        f"\nEstimated remaining time: "
                        f"{datetime.timedelta(seconds=estimated_remaining)}"
                    )
                    logging.info(
                        f"Out of the total replacements, {json_solutions_counter}"
                        f" solutions were found in the user_solutions file,"
                        f" which is {proportion:.2f}% of the total replacements."
                    )
                    logging.info(
                        f"Completed {percent_complete:.2f}% of files."
                    )
                    bar.update()

        elapsed_time = datetime.datetime.now() - start_time
        logging.info(
            f"\nNormalization completed. Total files normalized:"
            f" {total_processed_files}. Total replacements made:"
            f" {total_replacements}. Total time taken: {elapsed_time}.\n"
        )
        # Update the progress bar within the loop
        for subdir, dirs, files in os.walk(target_directory):
            for file in files:
                if file.endswith('.txt'):
                    # Process the file
                    bar.update()
    # Close the progress bar when done
    bar.close()

if __name__ == "__main__":
    config = load_config()
    directory = config["directories"]["working_directory"]
    log_level = config["logging"]["level"]
    context_size = config["settings"]["context_size"]
    unicode_replacements = config.get('unicode_replacements', {})

    configure_logging(log_level)
    main(directory, context_size, unicode_replacements)
