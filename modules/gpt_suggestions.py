"""
This file contains the GPTSuggestions class, which is responsible for retrieving suggestions from GPT-4.
This class is only instantiated if the user has enabled the GPT-4 suggestions in the config.toml file.
It sends the context to the GPT-4 API and retrieves the suggestions as to what should replace the $ symbol.
The suggestion is then displayed to the user.
"""
import os
import openai


class GPTSuggestions:
    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key is None:
            raise ValueError("No OpenAI API key found in environment variables")

        openai.api_key = self.api_key

        # Get the language model type from config
        self.model_type = config.get('OpenAI_integration', 'language_model')

        if self.model_type == "GPT4":
            self.model = "text-davinci-004"  # Replace with the actual model identifier for GPT-4
        elif self.model_type == "Mistral7b":
            self.model = "text-mistral-7b"  # Replace with the actual model identifier for Mistral 7b
        else:
            raise ValueError("Invalid language model type specified")


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
