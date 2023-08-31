python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install toml Pool nltk rich openai atomicwrites Progress art text2art Levenshtein prompt_toolkit

python modules/main.py
