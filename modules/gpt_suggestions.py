import os
import logging
from openai import OpenAI

class MissingAPIKeyError(Exception):
    def __init__(self):
        message = "OpenAI API key not found in environment variables. Please set the OPENAI_API_KEY environment variable."
        super().__init__(message)

class GPTSuggestions:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key is None:
            raise MissingAPIKeyError()

        # Instantiate the OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        # Get the language model type from config
        self.model_type = config.get('OpenAI_integration', 'language_model')
        self.model = "gpt-4" if self.model_type == "GPT-4" else "gpt-3.5-turbo"

    def get_suggestion(self, word, context):
        try:
            system_message = {"role": "system", "content": "You are a seasoned scholar in the humanities specialized in early modern languages. Your role is to help deciphering abbreviations from Renaissance and early modern printed books."}
            user_message = {"role": "user", "content": f"Problematic Word: {word}\nContext: {context}"}

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[system_message, user_message],
                max_tokens=50
            )

            if response and 'choices' in response and len(response['choices']) > 0 and 'message' in response['choices'][0]:
                return response['choices'][0]['message']['content'].strip()
            else:
                return "No response generated"
        except Exception as e:
            self.logger.exception("Error in generating GPT suggestion")
            return f"Error in generating suggestion: {e}"

    def print_suggestion(self, context, suggestion):
        print("\n\n")
        print(f"[bold]GPT Suggestion:[/bold] {suggestion}")
        print("\n\n")

    def get_and_print_suggestion(self, context):
        suggestion = self.get_suggestion(context)
        self.print_suggestion(context, suggestion)
        return suggestion
