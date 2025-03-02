import logging
import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class GPTSuggestions:
    """
    GPTSuggestions integrates with either the OpenAI API or the Mistral API to provide
    expansion suggestions for abbreviations. The provider, model, and suggestion count
    are specified in the configuration (e.g., config.toml), while API keys and endpoints
    are read from environment variables (loaded from your .env file).

    The prompt sent to the language model now includes additional contextual information,
    such as language, title, date, and source details (if provided in the metadata).

    Required configuration keys under [language_model_integration]:
      - provider: "openai" or "mistral"
      - model_name: the model to use (e.g., "gpt-4" for OpenAI or a valid Mistral model)
      - suggestion_count: number of suggestions to request

    Environment Variables:
      - For OpenAI: OPENAI_API_KEY must be set.
      - For Mistral: MISTRAL_API_KEY and MISTRAL_ENDPOINT must be set.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GPTSuggestions with the provided configuration.

        Args:
            config: A configuration dictionary containing language_model_integration settings.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        self.provider = config.get("language_model_integration", "provider", "openai").lower()
        self.suggestion_count = config.get("language_model_integration", "suggestion_count", 3)
        self.model = config.get("language_model_integration", "model_name")
        if not self.model:
            raise ValueError("Model name must be specified in config.toml under [language_model_integration].")

        if self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY must be set in your environment.")
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == "mistral":
            self.api_key = os.getenv("MISTRAL_API_KEY")
            self.endpoint = os.getenv("MISTRAL_ENDPOINT")
            if not self.api_key or not self.endpoint:
                raise ValueError("MISTRAL_API_KEY and MISTRAL_ENDPOINT must be set in your environment.")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_expansions(self, abbreviation: str, context_before: str, context_after: str,
                       metadata: Dict[str, Any] = None) -> List[str]:
        """
        Request single-word expansions from the selected language model, returning each expansion separately.

        Args:
            abbreviation: The abbreviation to expand.
            context_before: Text preceding the abbreviation.
            context_after: Text following the abbreviation.
            metadata: Optional dictionary with contextual info (e.g., language, title, date, source).

        Returns:
            A list of single-word expansion strings.

        Raises:
            Exception: Propagates any errors from the API call.
        """
        context_info = ""
        if metadata:
            if 'language' in metadata:
                context_info += f"Language: {metadata['language']}\n"
            if 'title' in metadata:
                context_info += f"Title: {metadata['title']}\n"
            if 'date' in metadata:
                context_info += f"Date: {metadata['date']}\n"
            if 'source' in metadata:
                context_info += f"Source: {metadata['source']}\n"

        # Prompt explicitly requires single-word expansions, comma-separated
        prompt = (
            f"Expand the following abbreviation into exactly {self.suggestion_count} distinct single-word expansions. "
            f"Separate each expansion by a comma only, with no extra text.\n\n"
            f"Abbreviation: {abbreviation}\n"
            f"Context before: {context_before}\n"
            f"Context after: {context_after}\n"
            f"Additional information:\n{context_info}"
        )

        if self.provider == "openai":
            try:
                # Request just one completion and parse the expansions from its content
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in early modern abbreviations."},
                        {"role": "user", "content": prompt}
                    ],
                    n=1,  # Only one response chunk
                    temperature=0.7
                )
                expansion_text = response.choices[0].message.content.strip()
                # Split on commas, ensuring each result is a single word
                suggestions = [item.strip() for item in expansion_text.split(',') if item.strip()]
                return suggestions

            except Exception as e:
                self.logger.error(f"Error calling OpenAI API: {e}")
                raise e

        elif self.provider == "mistral":
            try:
                payload = {
                    "prompt": prompt,
                    "model": self.model,
                    "num_outputs": 1,  # same idea: single completion
                    "temperature": 0.7
                }
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                # Mistral is expected to return expansions in data["outputs"][0]
                # so we parse them similarly (adapt as needed based on actual Mistral format)
                expansion_text = data.get("outputs", [""])[0].strip()
                suggestions = [item.strip() for item in expansion_text.split(',') if item.strip()]
                return suggestions

            except Exception as e:
                self.logger.error(f"Error calling Mistral API: {e}")
                raise e

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")