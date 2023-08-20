Given the complexity of the task, we will need to create several Python files to handle different parts of the application. Here are the core classes, functions, and methods that will be necessary:

1. `config.py`: This file will handle the reading of the `config.toml` file and provide an easy way for other parts of the application to access the configuration settings.

2. `unicode_replacement.py`: This file will handle the Unicode replacement functionality. It will include a function to replace and/or delete Unicode characters based on the mappings provided in the `config.toml` file.

3. `word_normalization.py`: This file will handle the word normalization functionality. It will include functions to normalize abbreviated words based on the dictionaries provided, and to prompt the user for input when necessary.

4. `gpt_suggestions.py`: This file will handle the GPT suggestions functionality. It will include a function to generate a replacement suggestion from GPT based on the context of the abbreviated word.

5. `main.py`: This will be the entry point of the application. It will use the functions from the other files to perform the necessary tasks.

Now, let's start with the `main.py` file:

main.py
