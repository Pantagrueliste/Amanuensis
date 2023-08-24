import os
import toml
import art
from toml.decoder import TomlDecodeError
from art import text2art


class PickleableTomlDecoder(toml.TomlDecoder):
    def get_empty_inline_table(self):
        return self.get_empty_table()


class Config:
    def __init__(self, file_path="config.toml"):
        self.file_path = file_path
        self.settings = self._read_config()
        self.print_config_recap()

    def _read_config(self):
        """Read the configuration file"""
        try:
            config = toml.load(self.file_path, decoder=PickleableTomlDecoder())
            print(text2art("Amanuensis"))
            return config
        except TomlDecodeError:
            raise Exception(
                "Error decoding TOML file. Please check the configuration file format."
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file '{self.file_path}' not found.")

    def get(self, section, key=None):
        try:
            if key:
                return self.settings[section][key]
            return self.settings[section]
        except KeyError:
            raise KeyError(
                f"Section '{section}' or key '{key}' not found in configuration file."
            )

    def print_config_recap(self):
        print("\nCurrent Settings:")

        replacements_on = self.settings.get("unicode_replacements", {}).get(
            "replacements_on", False
        )
        print(
            f" - Unicode Replacement Process: {'Enabled' if replacements_on else 'Disabled'}"
        )

        deletion_chars = len(
            self.settings.get("unicode_replacements", {}).get(
                "characters_to_delete", []
            )
        )
        print(f" - Number of Characters Defined for Deletion: {deletion_chars}")

        replacement_chars = len(
            self.settings.get("unicode_replacements", {}).get(
                "characters_to_replace", {}
            )
        )
        print(f" - Number of Characters Defined for Replacement: {replacement_chars}")

        gpt_suggestions = self.settings.get("OpenAI_integration", {}).get(
            "gpt_suggestions", False
        )
        print(
            f" - GPT Suggestions Option: {'Activated' if gpt_suggestions else 'Deactivated'}"
        )

        context_size = self.settings.get("settings", {}).get("context_size", 20)
        print(f" - Context Size for Abbreviated Words: {context_size} words\n")

    def validate_paths(self):
        input_path = self.get("paths", "input_path")
        output_path = self.get("paths", "output_path")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path '{input_path}' not found.")
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output path '{output_path}' not found.")
