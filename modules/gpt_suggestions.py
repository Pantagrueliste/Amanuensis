"""
This file contains the GPTSuggestions class, which is responsible for retrieving suggestions from GPT-4.
This class is only instantiated if the user has enabled the GPT-4 suggestions in the config.toml file.
It sends the context to the GPT-4 API and retrieves the suggestions as to what should replace the $ symbol.
The suggestion is then displayed to the user.
"""
import os
import openai


class GPTSuggestions:
    def __init__(self):
        # Get API key from environment variable
        self.api_key = os.getenv('OPENAI_API_KEY')

        if self.api_key is None:
            raise ValueError("No OpenAI API key found in environment variables")

        # Use the API key
        openai.api_key = self.api_key
        self.gpt = openai.Completion()


    def get_suggestion(self, context):
        """
        Get a suggestion from GPT-4.
        """
        suggestion = self.gpt.get_top_reply(context)
        return suggestion

    @staticmethod
    def print_suggestion(self, context, suggestion):
        """
        Print the suggestion to the user.
        """
        print("\n\n")
        print(f"[bold]GPT Suggestion:[/bold] {suggestion}")
        print("\n\n")

    def get_and_print_suggestion(self, context):
        """
        Get and print a suggestion from GPT-4.
        """
        suggestion = self.get_suggestion(context)
        self.print_suggestion(context, suggestion)
        return suggestion
