# Amanuensis 2.0: TEI XML Abbreviation Expansion Tool

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8224585.svg)](https://doi.org/10.5281/zenodo.8224585)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

Amanuensis, *noun*. /əˌmænjuˈensɪs/.
Early 17th cent.: Latin, from _a manu_ (short for secretary) and -ensis 'belonging to'.

1. a person who writes down your words when you cannot write.
2. a literary assistant, especially one who writes, types for somebody or copies text.

---

## Amanuensis 2.0: New Version

Amanuensis 2.0 is a significant upgrade from the original version, focusing specifically on TEI XML processing for early modern abbreviations. This new version provides a modern, modular architecture with enhanced capabilities for working with structured documents.

### New Features in Version 2.0

- **XML-Native Processing**: Works directly with XML nodes without extracting to plain text, preserving the structure and relationships between elements
- **TEI-Aware Handling**: Special handling for TEI XML abbreviation structures including `<abbr>`, `<g>`, and `<am>` elements
- **Smart Suggestion System**: Combine dictionary lookups, pattern matching, WordNet, and language models for better expansions
- **Interactive Interface**: User-friendly command-line interface for reviewing and selecting expansions
- **Dataset Creation**: Build datasets for training language models on abbreviation expansion
- **Comprehensive Test Suite**: Extensive testing framework to ensure reliability
- **Modern Architecture**: Modular, maintainable code structure

### XML-Native Processing Approach

In version 2.0, we've completely redesigned how TEI documents are processed to preserve structural information:

1. **Direct XML Manipulation**: Work directly with XML nodes instead of extracting to plain text
2. **Node Relationships**: Maintain parent-child relationships between elements
3. **Structure Preservation**: Handle complex TEI structures like `<choice>`, `<abbr>`, `<expan>`, `<am>`, `<ex>` properly
4. **Special Element Support**: Properly handle special elements like `<g ref="char:cmbAbbrStroke">` for macrons and other early modern abbreviation markers
5. **XPath Navigation**: Use XPath for precise element location rather than string searching

## Original Features

Amanuensis is an application designed to accelerate normalization tasks in large historical corpora. It increases legibility by expanding abbreviations and replacing unicode characters in a systematic and context-sensitive way. This type of pre-processing is instrumental to subsequent digital analyses and manipulations.

- **Unicode Character Replacement**: A powerful conversion tool to clean up text by removing and/or replacing undesirable characters.
- **Dynamic Word Normalization**: Expanding abbreviated words using Natural Language Processing, human inputs, and Large Language Models.
- **Comprehensive Logging**: Every single modification is meticulously tracked and stored in accessible json files, enabling further statistical analysis.

## Installation

### Prerequisites

- Python 3.10 or higher
- Required packages (install with pip):
  - toml
  - lxml
  - rich
  - nltk

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/amanuensis.git
   cd amanuensis
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Download NLTK data:
   ```bash
   python -c "import nltk; nltk.download('wordnet')"
   ```

4. (Optional) Set up OpenAI API for enhanced suggestions:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

## Usage

### Using Amanuensis 2.0

```bash
python amanuensis.py
```

This will launch the interactive interface for the new version.

### Command Line Options

```bash
python amanuensis.py --help
```

Options:
- `--config, -c`: Path to configuration file (default: config.toml)
- `--input, -i`: Input directory containing TEI XML files
- `--output, -o`: Output directory for processed files
- `--quiet, -q`: Run in non-interactive mode
- `--verbose, -v`: Enable verbose logging
- `--process, -p`: Process a specific TEI XML file

### Examples

Process a specific file:
```bash
python amanuensis.py --process samples/document.xml
```

Process all files in a directory:
```bash
python amanuensis.py --input /path/to/tei/files --output /path/to/output
```

### Using the Original Version

For the original version functionality:

```bash
./run.sh
```

## Configuration

Configuration is managed through the `config.toml` file. Key settings include:

- Input/output paths
- Language model settings
- User interface preferences
- Dataset creation options
- TEI XML processing settings

See `config.toml` for detailed configuration options.

## Roadmap

- **Multilingual Support**: Addition of French, Italian, Latin, and Spanish.
- **Beyond OpenAI**: Compatibility with competing APIs.
- **Documentation**: Basic documentation in English, French, and Spanish.
- **Web Interface**: Develop a web-based interface for easier interaction

Feel free to suggest new features in the Issues section.

## Dependencies

See requirements.txt

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the terms of the MIT license. For more details, see the [LICENSE](LICENSE.md) file.