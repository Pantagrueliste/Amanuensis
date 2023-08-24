# Amanuēsis: a normalization tool for early modern abbreviated texts
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8224585.svg)](https://doi.org/10.5281/zenodo.8224585)


Amanuēsis is a fairly robust Python application, tailored specifically for researchers in the Digital Humanities. Leveraging natural language and large language models, it is designed to accelerate normalization tasks for large-scale text data, transforming old and complex texts into a more digestible format. This preparation is crucial for further digital analysis and manipulation. With Amanuēsis, you can make your text data more accessible and easier to work with, using natural language and artificial intelligence to accelerate and streamline an ortherwise rebarbative process.

<img width="1792" alt="Screenshot 2023-07-31 at 18 59 01" src="https://github.com/Pantagrueliste/Amanuensis/assets/9995536/33ccccc5-4287-4874-891a-e57035e5418e">

## Features

- **Unicode Character Replacement**: A powerful conversion tool to clean up text by removing undesirable characters.
- **Dynamic Word Normalization**: Expanding abbreviated words using natural language processing, human inputs, and large language models to enhance legibility.
- **Parallel Processing**: Leveraging the the full potential of your multicore CPU, this feature makes large normalization tasks more manageable.
- **Comprehensive Logging**: Every single modification is meticulously traked and stored in accessible json files, enabling further analysis.
- **Batch Processing**: Tailored for efficiently converting very large volumes of text. 

## Upcoming Features

- ~~**Improved Robustness**: Improved error handling, code simplification.~~
- ~~**Increased Performance**: Async IO and multithreading.~~
- **Multilingual Support**: Addition of French, Italian, Latin, and Spanish.  
- ~~- **Increased Customization**: More options in TOML config file.~~
- **OpenAI API**: Optional step in the Dynamic Word Normalization leveraging Large Language Models such as GPT-4.
- **Documentation**: Basic documentation in English, French, and Spanish.

Feel free to suggest new features in the Issues section.

## Usage

To use Amanuēsis, simply clone this repository, navigate to the directory, and run `python amanuensis.py`. When prompted, enter the directory where your text files are located. The script will then normalize each file, line by line, applying the normalization function to each word. 

## Dependencies

See requirements.txt

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE.md) file.

---

Amanuensis, *noun*. /əˌmænjuˈensɪs/.  
Early 17th cent.: Latin, from _a manu_ (short for secretary) and -ensis ‘belonging to’.  
1. a person who writes down your words when you cannot write.
2. a literary assistant, especially one who writes, types for somebody or copies text.  
