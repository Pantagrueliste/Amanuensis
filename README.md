# Amanuēsis: a normalization tool for early modern abbreviated texts
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8224585.svg)](https://doi.org/10.5281/zenodo.8224585)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<!-- [![Qodana](https://github.com/Pantagrueliste/Amanuensis/actions/workflows/qodana_code_quality.yml/badge.svg)](https://github.com/Pantagrueliste/Amanuensis/actions/workflows/qodana_code_quality.yml)-->

Amanuensis, *noun*. /əˌmænjuˈensɪs/.
Early 17th cent.: Latin, from _a manu_ (short for secretary) and -ensis ‘belonging to’.

1. a person who writes down your words when you cannot write.
2. a literary assistant, especially one who writes, types for somebody or copies text.

---

Amanuēsis is an application designed to accelerate normalization tasks in large historical corpora. It makes text-data more legible by expanding abbreviations and replacing unicode characters in a systematic and context-sensitve way. This type of pre-processing is instrumental to the digital analysis and manipulation of historical documents. Amanuēsis is conceived to handle very large corpora rapidly, and is optimized to use the full potential of your multicore CPU. 

## Features

- **Unicode Character Replacement**: A powerful conversion tool to clean up text by removing and/or replacing
  undesirable characters.
- **Dynamic Word Normalization**: Expanding abbreviated words using Natural Language Processing, human inputs, and
  Large Language Models.
- **Parallel Processing**: Built with efficiency in mind, Amanuēsis uses parallel processing to make large normalization tasks more manageable.
- **Comprehensive Logging**: Every single modification is meticulously tracked and stored in accessible json files,
  enabling further statistical analysis.

## Roadmap

- **Multilingual Support**: Addition of French, Italian, Latin, and Spanish.
- **Beyond OpenAI**: Compatibility with competing APIs.
- **Documentation**: Basic documentation in English, French, and Spanish.

Feel free to suggest new features in the Issues section.

## Usage

To use Amanuēsis, simply clone this repository, navigate to the directory, and run `./run.sh`. Alternatively, you can
run the app directly from the modules/ folder `python main.py`. Make sure before to indicate the input and destination
paths in the config.toml file.

<img width="1205" alt="Screenshot 2023-08-26 at 17 03 30" src="https://github.com/Pantagrueliste/Amanuensis/assets/9995536/c257e5fc-b671-4b05-8f4c-193c80be8a5a">

## Dependencies

See requirements.txt

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE.md) file.
