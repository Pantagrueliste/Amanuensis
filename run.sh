python3 -m venv env
source env/bin/activate

pip install --upgrade pip
pip install toml Pool rich openai atomicwrites Progress art ijson text2art Levenshtein prompt_toolkit orjson pyahocorasick
python -m nltk.downloader wordnet

python modules/main.py
