Amanuensis, *noun*. /əˌmænjuˈensɪs/.  
Early 17th cent.: Latin, from (servus) a manu ‘(slave) at hand(writing), secretary’ + -ensis ‘belonging to’.  
1. a person who writes down your words when you cannot write.
2. an assistant, especially one who writes or types for somebody.  

# Amanuēsis: a normalization tool for early modern abbreviated texts
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8224585.svg)](https://doi.org/10.5281/zenodo.8224585)


Amanuēsis is a fairly robust Python application, tailored specifically for researchers in the Digital Humanities. Leveraging natural language and large language models, it is designed to accelerate normalization tasks for large-scale text data, transforming old and complex texts into a more digestible format. This preparation is crucial for further digital analysis and manipulation. With Amanuēsis, you can make your text data more accessible and easier to work with, using natural language and artificial intelligence to streamline an ortherwise rebarbative process..

<img width="1792" alt="Screenshot 2023-07-31 at 18 59 01" src="https://github.com/Pantagrueliste/Amanuensis/assets/9995536/33ccccc5-4287-4874-891a-e57035e5418e">

## Features

- **Unicode Character Replacement**: Powerful conversion tool cleanup the text from undesirable characters.
- **Dynamic Word Normalization**: Expands abbreviated words using natural language processing, human inputs, and large language models.
- **Parallel Processing**: Takles full advantage of your multicore CPU, converting excruciatingly long tasks into something manageable.
- **Exhausitve Logging**: Keeps track of every single modification in accessible json files.
- **Batch Processing**: Designed to convert large amounts of text files. 

## Upcoming Features

- ~~**Improved Robustness**: Improved error handling, code simplification.~~
- ~~**Increased Performance**: Async IO and multithreading.~~
- **Multilingual Support**: Addition of French, Italian, Latin, and Spanish.  
- ~~- **Increased Customization**: More options in TOML config file.~~
- **OpenAI API**: Optional step in the Dynamic Word Normalization leveraging Large Language Models such as GPT-4.
- **Documentation**: Basic documentation in English.

Feel free to suggest new features in the Issues section.

## Usage

To use Amanuēsis, simply clone this repository, navigate to the directory, and run `python amanuensis.py`. When prompted, enter the directory where your text files are located. The script will then normalize each file, line by line, applying the normalization function to each word. 

## Dependencies

- Python 3.7+
- NLTK
- Levenshtein
- colorama
- art
- toml
- Pool
- rich
- Progress
- text2art

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE.md) file.
