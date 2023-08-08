"""
This module normalizes early modern texts both by systematically replacing
specific characters and by offering ad hoc solutions using wordnet and
a user-defined dictionaries.
"""

import os
import sys
import csv
import json
import string
import datetime
import logging
import toml
from toml.decoder import TomlDecodeError

import nltk
from art import text2art
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from colorama import init, Fore, Back, Style
from progressbar import ProgressBar
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from multiprocessing import Pool

import Levenshtein


# Setting logging levels
MINIMAL_LOGGING = 1
VERBOSE_LOGGING = 2
STATISTIC_LOGGING = 3

LOGGING_LEVELS_MAP = {
    "minimal": logging.ERROR,
    "verbose": logging.INFO,
    "statistic": logging.DEBUG
}


json_solutions_counter = 0

# Progressbar global definition
progress = ProgressBar()

# Title
print(text2art("Amanuensis-alpha2"))

# Initialize colorama for colored console output
init(autoreset=True)

# Download wordnet corpus, used for word normalization
nltk.download('wordnet')

# Create a WordNetLemmatizer object, used for word normalization
lemmatizer = WordNetLemmatizer()

def read_config(file_path):
    """Read the configuration file"""
    try:
        config = toml.load(file_path)
        input_path = config['paths']['input_path']
        output_path = config['paths']['output_path']
        logging_level_key = config['logging']['level']
        logging_level = LOGGING_LEVELS_MAP.get(logging_level_key.lower(), logging.WARNING)  # Assuming LOGGING_LEVELS_MAP is defined
        context_size = config['settings']['context_size']
        unicode_replacements = config['unicode_replacements']
        replacements_on = unicode_replacements['replacements_on']
        characters_to_delete = unicode_replacements['characters_to_delete']
        characters_to_replace = unicode_replacements['characters_to_replace']

        # Validate the paths
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path '{input_path}' not found.")
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output path '{output_path}' not found.")

        return (input_path, output_path, logging_level, context_size,
                replacements_on, characters_to_delete, characters_to_replace)

    except TomlDecodeError:
        print("Error decoding TOML file. Please check the configuration file format.")
        sys.exit(1)
    except KeyError as e:
        print(f"Missing key in configuration: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

current_directory = os.path.dirname(os.path.abspath(__file__))
toml_file_path = os.path.join(current_directory, 'config.toml')

input_path, output_path, logging_level, context_size, replacements_on, characters_to_delete, characters_to_replace = read_config(toml_file_path)

print(current_directory, input_path, output_path, logging_level, context_size, replacements_on, characters_to_delete, characters_to_replace)

def apply_unicode_replacements(file_path,
                               replacements_on,
                               characters_to_delete,
                               characters_to_replace):

    """Applies Unicode replacements on the given file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    if replacements_on:
        # Delete specified characters
        for char in characters_to_delete:
            text = text.replace(char, "")

        # Apply specified replacements
        for original, replacement in characters_to_replace.items():
            text = text.replace(original, replacement)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(text)

def log_replacement(logger,
                    file_name,
                    line_number,
                    original_word,
                    replaced_word):

    with open(logger, 'a', encoding='utf-8') as log_file:
        log_entry = f"File: {file_name}, Line: {line_number}, Original: {original_word}, Replaced: {replaced_word}\n"
        log_file.write(log_entry)

def process_files(files,
                  replacements_on,
                  characters_to_delete,
                  characters_to_replace):

    """multiprocessing"""
    with Pool() as pool:
        pool.starmap(apply_unicode_replacements, zip(files, [replacements_on]*len(files), [characters_to_delete]*len(files), [characters_to_replace]*len(files)))


# Load user solutions from a JSON file.
# These are preferred solutions for word normalization.
try:
    with open('user_solutions.json', 'r', encoding='utf-8') as file:
        user_solutions = json.load(file)
except FileNotFoundError:
    user_solutions = {}

# Initialize logging
logging.basicConfig(
    filename='normalization.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)


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


def check_user_solutions(word_wo_punctuation,
                         user_solutions):
    """
    Check if the solution for the word without punctuation exists in user solutions.
    """
    if word_wo_punctuation in user_solutions and word_wo_punctuation not in ["the$"]:
        return user_solutions[word_wo_punctuation]
    return None


def check_unicode_replacement(word_wo_punctuation,
                              unicode_replacements):
    """
    Check if the solution for the word without punctuation exists in unicode replacements.
    """
    if word_wo_punctuation in unicode_replacements:
        return unicode_replacements[word_wo_punctuation]
    return None


def get_synsets_replacement(word_wo_punctuation,
                            trailing_punctuation,
                            lemmatizer):
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

def remove_punctuation_from_word(word):
    word_wo_punctuation, trailing_punctuation = remove_punctuation(word)
    return word_wo_punctuation, trailing_punctuation


def check_and_log_user_solution(word_wo_punctuation,
                                user_solutions,
                                file_name,
                                line_number,
                                word,
                                trailing_punctuation):

    user_solution = check_user_solutions(word_wo_punctuation, user_solutions)
    if user_solution is not None:
        logging.info(f"{Fore.GREEN}{file_name}, line {line_number}: '{word}' replaced with '{user_solution}' using a previous user solution")
        global json_solutions_counter
        json_solutions_counter += 1
        return user_solution + trailing_punctuation
    return None


def handle_synsets_replacement(word,
                               word_wo_punctuation,
                               trailing_punctuation,
                               lemmatizer,
                               file_name,
                               line_number,
                               user_solutions):

    synsets_replacement = get_synsets_replacement(word_wo_punctuation, trailing_punctuation, lemmatizer)
    if synsets_replacement is not None:
        if word_wo_punctuation not in user_solutions:
            message1 = f"The original word was '{Fore.RED + word + Style.RESET_ALL}'"
            message2 = f"in file '{file_name}' at line {line_number}. After replacing $, '{Fore.GREEN + synsets_replacement + Style.RESET_ALL}'"
            message3 = "is in the dictionary, saving as such."
            logging.info(f"{Fore.LIGHTBLACK_EX}{message1}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}{message2}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}{message3}{Style.RESET_ALL}")
            return synsets_replacement
        else:
            return user_solutions[word_wo_punctuation] + trailing_punctuation
    return None


def handle_user_input(word_wo_punctuation,
                      word_index,
                      context_size,
                      line_words,
                      file_name,
                      line_number):

    os.system('cls' if os.name == 'nt' else 'clear')
    message1 = f"Could not find a match for '{Fore.RED + word_wo_punctuation + Style.RESET_ALL}'"
    message2 = f"in the dictionary after trying both replacements. Found in file '{file_name}' at line {line_number}."
    print(f"{Fore.LIGHTBLACK_EX}{message1}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}{message2}{Style.RESET_ALL}")
    context_words = (line_words[max(0, word_index - 4):word_index] +
                     ['<...>'] +
                     line_words[word_index + 1:min(len(line_words), word_index + 5)])
    print("Context: ", ' '.join(context_words))

    while True:
        correct_word_prompt = HTML("<ansired>Please enter 'n' or 'm' to replace $, or enter the full replacement for '{}' or type 'quit' to exit the script, or '`' if you don't know:</ansired>\n".format(word_wo_punctuation))
        correct_word = prompt(correct_word_prompt)

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
            return word_wo_punctuation

        elif correct_word.lower() == 'n':
            correct_word = word_wo_punctuation.replace('$', 'n')
        elif correct_word.lower() == 'm':
            correct_word = word_wo_punctuation.replace('$', 'm')

        lev_distance = Levenshtein.distance(word_wo_punctuation.replace('$', ''), correct_word)
        if lev_distance > word_wo_punctuation.count('$') + 1:
            print(Fore.YELLOW + "Your input seems significantly different from the original word. Please confirm if this is correct.")
            confirmation = input("Type 'yes' to confirm, 'no' to input again: ").lower()
            while confirmation not in ['yes', 'no']:
                confirmation = input(Fore.RED + "Invalid response. Type 'yes' to confirm, 'no' to input again: ").lower()
            if confirmation == 'no':
                continue

        print()  # Adds a blank line for spacing

        break

    return correct_word

def log_and_save_user_solution(word_wo_punctuation,
                               correct_word,
                               trailing_punctuation,
                               file_name,
                               line_number,
                               word):

    global json_solutions_counter
    json_solutions_counter += 1

    logging.info(f"In the file '{file_name}' at line {line_number}, found a solution in the user_solutions file for the word '{word}'.")

    if word_wo_punctuation != "the$":
        user_solutions[word_wo_punctuation] = correct_word

    with open('user_solutions.json', 'w', encoding='utf-8') as file:
        json.dump(user_solutions, file)

    return correct_word + trailing_punctuation


def normalize_word(word, file_name,
                   line_number,
                   line_words,
                   word_index,
                   unicode_replacements,
                   logger,
                   context_size):

    original_word = word

    word_wo_punctuation, trailing_punctuation = remove_punctuation_from_word(word)

    user_solution = check_and_log_user_solution(word_wo_punctuation, user_solutions, file_name, line_number, word, trailing_punctuation)

    if user_solution is not None:
        return user_solution

    if '$' not in word_wo_punctuation:
        return word_wo_punctuation + trailing_punctuation

    synsets_replacement = handle_synsets_replacement(word, word_wo_punctuation, trailing_punctuation, lemmatizer, file_name, line_number, user_solutions)

    if synsets_replacement is not None:
        return synsets_replacement

    correct_word = handle_user_input(word_wo_punctuation, word_index, context_size, line_words, file_name, line_number)
    replacement_word = log_and_save_user_solution(word_wo_punctuation, correct_word, trailing_punctuation, file_name, line_number, word)

    logger.log(file_name, line_number, original_word, replacement_word)

    return replacement_word

def normalize_line(line,
                   file_name,
                   line_number,
                   unicode_replacements,
                   logger,
                   context_size):
    """
    This function normalizes a given line and logs the replacements made.
    """
    global json_solutions_counter
    line_words = line.split()
    for word_index, word in enumerate(line_words):
        if "$" in word:
            word = normalize_word(word, file_name, line_number, line_words, word_index, unicode_replacements, logger, context_size)
            line_words[word_index] = word

    return ' '.join(line_words)


def normalize_file(file_path,
                   unicode_replacements,
                   logger,
                   context_size):

    """
    This function normalizes a given file and logs the replacements made.
    """
    global json_solutions_counter
    file_name = os.path.basename(file_path)
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines):
        lines[line_number] = normalize_line(line, file_name, line_number, unicode_replacements, logger, context_size)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    return json_solutions_counter


class ReplacementLogger:
    def __init__(self, log_file):
        self.log_file = log_file

    def log(self, file_name, line_number, original_word, replaced_word):
        with open(self.log_file, 'a', encoding='utf-8') as log_file:
            log_entry = f"File: {file_name}, Line: {line_number}, Original: {original_word}, Replaced: {replaced_word}\n"
            log_file.write(log_entry)


def main():
    # Get config parameters
    input_path, output_path, logging_level, context_size, replacements_on, characters_to_delete, characters_to_replace = read_config('config.toml')

    # Define the path to the log file
    log_file = 'replacements.log'
    logger = ReplacementLogger(log_file)

    # Combine characters_to_delete and characters_to_replace into a single dictionary
    unicode_replacements = characters_to_replace.copy()
    for char in characters_to_delete:
        unicode_replacements[char] = ''

    # Print information about Unicode replacements
    if replacements_on:
        print("Running Unicode replacements...")
        print(f"Characters to delete: {characters_to_delete}")
        print(f"Characters to replace: {list(characters_to_replace.keys())}")

    # Count files for Unicode replacements and create progress bar
    file_count_replacements = sum(len(files) for _, _, files in os.walk(input_path) if any(fname.endswith('.txt') for fname in files))
    pbar_replacements = ProgressBar(maxval=file_count_replacements)
    pbar_replacements.start()


    processed_files = 0

    # Perform Unicode replacements on all files first
    for dirpath, dirnames, filenames in os.walk(input_path):
        for filename in filenames:
            if filename.endswith(".txt"):  # process only .txt files
                file_path = os.path.join(dirpath, filename)
                normalize_file(file_path, unicode_replacements, logger, context_size)
                processed_files += 1
                pbar_replacements.update(processed_files)

    pbar_replacements.finish()  # Finish progress bar for replacements

    # Reinitialize processed_files for normalization
    processed_files = 0

    # Count files for normalization and create progress bar
    file_count_normalization = sum(len(files) for _, _, files in os.walk(input_path) if any(fname.endswith('.txt') for fname in files))
    pbar_normalization = ProgressBar(maxval=file_count_normalization)
    pbar_normalization.start()

    # Normalize files after Unicode replacement step is finished
    processed_files = 0

    for dirpath, dirnames, filenames in os.walk(input_path):
        for filename in filenames:
            if filename.endswith(".txt"):  # process only .txt files
                file_path = os.path.join(dirpath, filename)
                normalize_file(file_path, unicode_replacements, logger, context_size)
                processed_files += 1
                pbar_normalization.update(processed_files)  # Update progress bar

    pbar_normalization.finish()  # Finish progress bar for normalization

    print(f"{Fore.GREEN}Normalization complete. Please check '{log_file}' for a log of the replacements.")



if __name__ == "__main__":
    main()
