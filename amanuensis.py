"""
This module normalizes early modern texts, by systematically replacing
specific characters and by offering ad hoc solutions using a wordnet and
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


json_solutions_counter = 0

# Progressbar global definition
progress = ProgressBar()

# Title
print(text2art("Amanuensis"))

# Initialize colorama for colored console output
init(autoreset=True)

# Download wordnet corpus, used for word normalization
nltk.download('wordnet')

# Create a WordNetLemmatizer object, used for word normalization
lemmatizer = WordNetLemmatizer()

def read_config(file_path):
    """Read the configuration file"""
    config = toml.load(file_path)
    working_directory = config['directories']['working_directory']
    logging_level = config['logging']['level']
    context_size = config['settings']['context_size']
    unicode_replacements = config['unicode_replacements']
    return working_directory, logging_level, context_size, unicode_replacements
toml_file_path = 'config.toml'

working_directory, logging_level, context_size, unicode_replacements = read_config(toml_file_path)
print(working_directory, logging_level, context_size, unicode_replacements)

def apply_unicode_replacements(file_path, unicode_replacements):
    """Applies Unicode replacements on the given file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    for original, replacement in unicode_replacements.items():
        text = text.replace(original, replacement)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(text)

def process_files(files, unicode_replacements):
    """multiprocessing"""
    with Pool() as pool:
        pool.starmap(apply_unicode_replacements, zip(files, [unicode_replacements]*len(files)))


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


def log_difficult_passage(file_path, line_number, context, csv_file='difficult_passages.csv'):
    """
    This function saves a difficult passage to a CSV file.
    It appends a row containing the file path, line number, and context of the difficult passage.
    """
    with open(csv_file, mode='a', newline='', encoding='utf-8') as csv_file_obj:
        writer = csv.writer(csv_file_obj)
        writer.writerow([file_path, line_number, context])


def check_user_solutions(word_wo_punctuation, user_solutions):
    """
    Check if the solution for the word without punctuation exists in user solutions.
    """
    if word_wo_punctuation in user_solutions and word_wo_punctuation not in ["the$"]:
        return user_solutions[word_wo_punctuation]
    return None


def check_unicode_replacement(word_wo_punctuation, unicode_replacements):
    """
    Check if the solution for the word without punctuation exists in unicode replacements.
    """
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

# added in the normalize_word simplification camplaign.

def remove_punctuation_from_word(word):
    word_wo_punctuation, trailing_punctuation = remove_punctuation(word)
    return word_wo_punctuation, trailing_punctuation


def check_and_log_user_solution(word_wo_punctuation, user_solutions, file_name, line_number, word, trailing_punctuation):
    user_solution = check_user_solutions(word_wo_punctuation, user_solutions)
    if user_solution is not None:
        logging.info(f"{Fore.GREEN}{file_name}, line {line_number}: '{word}' replaced with '{user_solution}' using a previous user solution")
        global json_solutions_counter
        json_solutions_counter += 1
        return user_solution + trailing_punctuation
    return None


def handle_synsets_replacement(word, word_wo_punctuation, trailing_punctuation, lemmatizer, file_name, line_number, user_solutions):
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


def handle_user_input(word_wo_punctuation, word_index, context_size, line_words, file_name, line_number):
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

def log_and_save_user_solution(word_wo_punctuation, correct_word, trailing_punctuation, file_name, line_number, word):
    global json_solutions_counter
    json_solutions_counter += 1

    logging.info(f"In the file '{file_name}' at line {line_number}, found a solution in the user_solutions file for the word '{word}'.")

    if word_wo_punctuation != "the$":
        user_solutions[word_wo_punctuation] = correct_word

    with open('user_solutions.json', 'w', encoding='utf-8') as file:
        json.dump(user_solutions, file)

    return correct_word + trailing_punctuation


def normalize_word(word, file_name, line_number, line_words, word_index, unicode_replacements, replacement_log, context_size):
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
    return log_and_save_user_solution(word_wo_punctuation, correct_word, trailing_punctuation, file_name, line_number, word)

def normalize_line(line, file_name, line_number, unicode_replacements, replacement_log, context_size):
    """
    This function normalizes a given line and logs the replacements made.
    """
    global json_solutions_counter
    line_words = line.split()
    for word_index, word in enumerate(line_words):
        if "$" in word:
            word = normalize_word(word, file_name, line_number, line_words, word_index, unicode_replacements, replacement_log, context_size)
            line_words[word_index] = word

    return ' '.join(line_words)


def normalize_file(file_path, unicode_replacements, replacement_log, context_size):
    """
    This function normalizes a given file and logs the replacements made.
    """
    global json_solutions_counter
    file_name = os.path.basename(file_path)
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines):
        lines[line_number] = normalize_line(line, file_name, line_number, unicode_replacements, replacement_log, context_size)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    return json_solutions_counter

def main():
    # Load config file
    try:
        with open('config.toml', 'r', encoding='utf-8') as file:
            config = toml.loads(file.read())
    except TomlDecodeError as error:
        print(f"Error while parsing config file: {error}")
        sys.exit()

    # Get config parameters
    working_directory = config.get('directories', {}).get('working_directory', [])
    unicode_replacements = config.get('unicode_replacements', {})
    context_size = config.get('settings', {}).get('context_size', 5)
    replacement_log = config.get('settings', {}).get('replacement_log', 'replacement_log.csv')

    # Print information about Unicode replacements
    if unicode_replacements:
        print("Running Unicode replacements...")
        print(f"Characters to replace: {list(unicode_replacements.keys())}")

    # Count files for Unicode replacements and create progress bar
    file_count_replacements = sum(len(files) for _, _, files in os.walk(working_directory) if any(fname.endswith('.txt') for fname in files))
    pbar_replacements = ProgressBar(maxval=file_count_replacements)
    pbar_replacements.start()

    # Perform Unicode replacements on all files first
    processed_files = 0
    for dirpath, dirnames, filenames in os.walk(working_directory):
        for filename in filenames:
            if filename.endswith(".txt"):  # process only .txt files
                file_path = os.path.join(dirpath, filename)
                if unicode_replacements:
                    apply_unicode_replacements(file_path, unicode_replacements)  # Apply Unicode replacements
                processed_files += 1
                pbar_replacements.update(processed_files)  # Update progress bar

    pbar_replacements.finish()  # Finish progress bar for replacements

    # Count files for normalization and create progress bar
    file_count_normalization = sum(len(files) for _, _, files in os.walk(working_directory) if any(fname.endswith('.txt') for fname in files))
    pbar_normalization = ProgressBar(maxval=file_count_normalization)
    pbar_normalization.start()

    # Normalize files after Unicode replacement step is finished
    processed_files = 0
    for dirpath, dirnames, filenames in os.walk(working_directory):
        for filename in filenames:
            if filename.endswith(".txt"):  # process only .txt files
                file_path = os.path.join(dirpath, filename)
                normalize_file(file_path, unicode_replacements, replacement_log, context_size)
                processed_files += 1
                pbar_normalization.update(processed_files)  # Update progress bar

    pbar_normalization.finish()  # Finish progress bar for normalization

    print(f"{Fore.GREEN}Normalization complete. Please check '{replacement_log}' for a log of the replacements.")

if __name__ == "__main__":
    main()
