import os
import logging
from typing import List, Dict, Any
import json

# Import OpenAI conditionally
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import httpx conditionally
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

class MissingAPIKeyError(Exception):
    def __init__(self, provider):
        message = f"{provider} API key not found in environment variables. Please set the {provider.upper()}_API_KEY environment variable."
        super().__init__(message)

class GPTSuggestions:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Check for OpenAI integration
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.mistral_key = os.getenv('MISTRAL_API_KEY')
        
        # Provider flags
        self.openai_available = OPENAI_AVAILABLE and self.openai_key is not None
        self.mistral_available = HTTPX_AVAILABLE and self.mistral_key is not None
        
        # Log availability
        if not self.openai_available:
            self.logger.warning("OpenAI integration not available. Install package or set API key.")
        if not self.mistral_available:
            self.logger.warning("Mistral integration not available. Install httpx or set API key.")
            
        # Setup OpenAI client if available
        if self.openai_available:
            self.openai_client = OpenAI(api_key=self.openai_key)
            self.openai_model = config.get('language_model_integration.openai', 'model_name', 'gpt-4')
        
        # Get config for Mistral
        if self.mistral_available:
            self.mistral_model = config.get('language_model_integration.mistral', 'model_name', 'mistral-medium')
            self.mistral_api_base = config.get('language_model_integration.mistral', 'api_base', 'https://api.mistral.ai/v1')

    def get_suggestions(self, word: str, context_before: str = "", context_after: str = "", metadata: Dict[str, Any] = None) -> List[str]:
        """
        Generate suggestions for an abbreviation using the configured LLM provider.
        
        Args:
            word: The abbreviated text
            context_before: Text before the abbreviation
            context_after: Text after the abbreviation
            metadata: Additional information about the abbreviation
            
        Returns:
            List of suggested expansions
        """
        # Choose provider based on availability and configuration
        provider = self.config.get('language_model_integration', 'provider', 'openai').lower()
        
        context = f"{context_before} {word} {context_after}"
        
        if provider == 'openai' and self.openai_available:
            return self._query_openai(word, context_before, context_after)
        elif provider == 'mistral' and self.mistral_available:
            return self._query_mistral(word, context_before, context_after)
        else:
            # Fallback to simple pattern-based expansion
            self.logger.warning(f"Provider {provider} not available, using fallback")
            return [word.replace('$', 'n').replace('õ', 'on')]

    def _query_openai(self, word: str, context_before: str, context_after: str) -> List[str]:
        """
        Query OpenAI API for abbreviation expansion suggestions.
        """
        if not self.openai_available:
            self.logger.error("OpenAI integration not available")
            return []
            
        try:
            # Get the prompt template from config
            prompt_template = self.config.get(
                'language_model_integration.prompts', 
                'single_template', 
                """
                Expand the abbreviated word '{abbr}' in the following context:
                Context before: {context_before}
                Abbreviated word: {abbr}
                Context after: {context_after}
                
                Provide 1-3 possible expansions, separated by commas, ordered by likelihood.
                """
            )
            
            # Format the prompt
            prompt = prompt_template.format(
                abbr=word,
                context_before=context_before,
                context_after=context_after
            )
            
            # Get system message from config
            system_message = self.config.get(
                'language_model_integration.openai', 
                'system_message', 
                "You are a linguist specializing in early modern texts. Your task is to expand abbreviated words based on context."
            )
            
            # Make API call
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('language_model_integration', 'max_tokens', 50),
                temperature=self.config.get('language_model_integration', 'suggestion_temperature', 0.3),
            )
            
            # Extract suggestions
            if response.choices and response.choices[0].message:
                suggestions_text = response.choices[0].message.content.strip()
                # Split by commas and clean up
                suggestions = [s.strip() for s in suggestions_text.split(',')]
                return suggestions
                
            return []
            
        except Exception as e:
            self.logger.error(f"Error querying OpenAI API: {e}")
            return []
            
    def _query_mistral(self, word: str, context_before: str, context_after: str) -> List[str]:
        """
        Query Mistral API for abbreviation expansion suggestions.
        """
        if not self.mistral_available:
            self.logger.error("Mistral integration not available")
            return []
            
        try:
            # Get the prompt template from config
            prompt_template = self.config.get(
                'language_model_integration.prompts', 
                'single_template', 
                """
                Expand the abbreviated word '{abbr}' in the following context:
                Context before: {context_before}
                Abbreviated word: {abbr}
                Context after: {context_after}
                
                Provide 1-3 possible expansions, separated by commas, ordered by likelihood.
                """
            )
            
            # Format the prompt
            prompt = prompt_template.format(
                abbr=word,
                context_before=context_before,
                context_after=context_after
            )
            
            # Get system message from config
            system_message = self.config.get(
                'language_model_integration.mistral', 
                'system_message', 
                "You are a linguist specializing in early modern texts. Your task is to expand abbreviated words based on context."
            )
            
            # Make API call
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.mistral_key}"
            }
            
            data = {
                "model": self.mistral_model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.config.get('language_model_integration', 'max_tokens', 50),
                "temperature": self.config.get('language_model_integration', 'suggestion_temperature', 0.3),
            }
            
            timeout = self.config.get('language_model_integration', 'request_timeout', 30)
            
            with httpx.Client(timeout=timeout) as client:
                response = client.post(f"{self.mistral_api_base}/chat/completions", json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            # Extract suggestions
            if 'choices' in result and result['choices'] and 'message' in result['choices'][0]:
                suggestions_text = result['choices'][0]['message']['content'].strip()
                # Split by commas and clean up
                suggestions = [s.strip() for s in suggestions_text.split(',')]
                return suggestions
                
            return []
            
        except Exception as e:
            self.logger.error(f"Error querying Mistral API: {e}")
            return []