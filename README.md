Amanuensis, *noun*. /əˌmænjuˈensɪs/.  
Early 17th cent.: Latin, from (servus) a manu ‘(slave) at hand(writing), secretary’ + -ensis ‘belonging to’.  
1. a person who writes down your words when you cannot write.
2. an assistant, especially one who writes or types for somebody.  

# Amanuensis: A human-supervised normalization tool for early modern abbreviated texts

Amanuensis is a fairly robust Python application, tailored specifically for researchers and users in the Digital Humanities. It is designed to accelerate normalization tasks for large-scale text data, transforming old and complex texts into a more digestible format. This preparation is crucial for further digital analysis and manipulation. With Amanuensis, you can make your text data more accessible and easier to work with.

<img width="1792" alt="Screenshot 2023-07-31 at 18 59 01" src="https://github.com/Pantagrueliste/Amanuensis/assets/9995536/33ccccc5-4287-4874-891a-e57035e5418e">

## Features

- **Unicode Replacement**: Handles a customizable dictionary of unicode characters and transforms them into understandable text representations.
- **Dynamic Word Normalization**: Changes words that contain special characters into valid English words.
- **Interactive Correction**: If a word can't be automatically normalized, the application prompts the user for input.
- **Progress Stats**: Offers real-time statistics like elapsed time, estimated remaining time, and percentage of files processed to keep you informed about the normalization process.
- **Batch Processing**: Processes all text files in a given directory, saving the output into a "FinalText" directory.
- **Difficulty Log**: Logs difficult passages for later review and analysis.

## Upcoming Features

- **Improved Robustness**: Improved error handling, code simplification.
- **Multilingual Support**: Addition of French, Italian, and Spanish.
- **Increased Customization**: More options in TOML config file.
- **OpenAI API**: Optional step in the Dynamic Word Normalization leveraging Large Language Models such as GPT-4.
- **Documentation**: Basic documentation in English.
- **Gamification**: Improved UX for a better user engagement.

## Usage

To use Amanuensis, simply clone this repository, navigate to the directory, and run `python amanuensis.py`. When prompted, enter the directory where your text files are located. The script will then normalize each file, line by line, applying the normalization function to each word. 

## Dependencies

- Python 3.7+
- NLTK
- Levenshtein
- colorama
- tqdm
- art

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE.md) file.
