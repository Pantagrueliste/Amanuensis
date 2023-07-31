# Amanuensis: A human-supervised normalization tool for early modern abbreviated texts

Amanuensis is a fairly robust Python application tailored for researchers and users in the Digital Humanities who need to process and normalize large amounts of text data. With Amanuensis, you can transform old and complex texts into a more digestible format, preparing them for further digital analysis and manipulation. 

## Features

- **Unicode Replacement**: Handles various unicode characters and transforms them into understandable text representations.
- **Dynamic Word Normalization**: Changes words that contain special characters into valid English words.
- **Interactive Correction**: If a word can't be automatically normalized, the application prompts the user for input.
- **Progress Stats**: Offers real-time statistics like elapsed time, estimated remaining time, and percentage of files processed to keep you informed about the normalization process.
- **Batch Processing**: Processes all text files in a given directory, saving the output into a "FinalText" directory.
- **Difficulty Log**: Logs difficult passages for later review and analysis.

## Upcoming Features

- **Customization**: Enables users to adapt Amanuensis to their specific needs with a TOML config file.
- **Robustness**: Robsntness with Logging features and improved error handling.
- **Documentation**: Basic documentation in English, French, Spanish, and Italian.
- **Gamification**: Improved UX for a better user engagement.

## Usage

To use Amanuensis, simply clone this repository, navigate to the directory, and run `python main.py`. When prompted, enter the directory where your text files are located. The script will then normalize each file, line by line, applying the normalization function to each word. 

## Dependencies

- Python 3.7+
- NLTK
- Levenshtein
- colorama

## Contributing

Contributions are welcome! Please feel free to submit a pull request.
