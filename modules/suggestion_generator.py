"""
Suggestion Generator - Generates expansion suggestions for abbreviations
focusing exclusively on dictionary-based approaches
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import random

# Try to import NLTK for advanced NLP
try:
    import nltk
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logging.warning("NLTK not available. Some suggestion features will be limited.")


class SuggestionGenerator:
    """
    Generates expansion suggestions for abbreviations using dictionary-based methods,
    WordNet, and language models. Pattern matching has been removed.
    """
    
    def __init__(self, config):
        """
        Initialize the suggestion generator with configuration.
        
        Args:
            config: Configuration object with suggestion settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Load settings
        self.language = config.get('settings', 'language', 'eng')
        self.use_wordnet = config.get('settings', 'use_wordnet', True) and NLTK_AVAILABLE
        
        # Load language model settings
        self.lm_enabled = config.get('language_model_integration', 'enabled', False)
        self.lm_provider = config.get('language_model_integration', 'provider', 'openai')
        self.lm_model = config.get('language_model_integration', 'model_name', 'gpt-4')
        self.suggestion_count = config.get('language_model_integration', 'suggestion_count', 3)
        
        # Set up expansion sources
        self.abbreviation_dict = self._load_abbreviation_dictionary()
        self.user_solutions = self._load_user_solutions()
        
        # Confidence scores for different sources - prioritizing dictionaries
        self.confidence_scores = {
            'user_dictionary': 0.98,   # Highest confidence for user-verified solutions
            'dictionary': 0.95,        # Very high confidence for standard dictionary
            'language_model': 0.8,     # High confidence for LLM suggestions
            'wordnet': 0.5,            # Lower confidence for wordnet
            'rule_based': 0.4          # Lowest confidence
        }
        
        # Statistics
        self.stats = {
            'total_suggestions': 0,
            'user_dictionary_matches': 0,
            'dictionary_matches': 0,
            'wordnet_suggestions': 0,
            'lm_suggestions': 0,
            'failed_abbreviations': 0
        }
    
    def _load_abbreviation_dictionary(self) -> Dict[str, List[str]]:
        """
        Load abbreviation dictionary from data files.
        
        Returns:
            Dictionary mapping abbreviations to possible expansions
        """
        try:
            # Try to load from configured path
            dict_path = self.config.get(
                'data', 
                'abbreviation_dictionary_path', 
                'data/abbreviation_dictionary.json'
            )
            
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Fallback to default dictionary
            return {
                "co$": ["con"],
                "y$": ["yt"],
                "w$": ["with"],
                "q$": ["que"],
                "p$": ["per", "par"],
                "$": ["n", "m"],
                "wch": ["which"],
                "sr": ["sir"],
                "ye": ["the"],
                "yt": ["that"],
                "wt": ["what"],
                "mr": ["master"]
            }
        
        except Exception as e:
            self.logger.error(f"Error loading abbreviation dictionary: {e}")
            return {}
    
    def _load_user_solutions(self) -> Dict[str, str]:
        """
        Load user solutions from user_solution.json.
        
        Returns:
            Dictionary mapping abbreviated forms to verified expansions
        """
        try:
            # Try to load from configured path
            user_solution_path = self.config.get(
                'data', 
                'user_solution_path', 
                'data/user_solution.json'
            )
            
            if os.path.exists(user_solution_path):
                with open(user_solution_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Return empty dict if file doesn't exist
            return {}
            
        except Exception as e:
            self.logger.error(f"Error loading user solutions: {e}")
            return {}
    
    def generate_suggestions(self, 
                             abbreviation: str, 
                             context_before: str = '', 
                             context_after: str = '',
                             metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Generate expansion suggestions for an abbreviation.
        
        Args:
            abbreviation: The abbreviated text
            context_before: Text context before the abbreviation
            context_after: Text context after the abbreviation
            metadata: Optional metadata about the source
            
        Returns:
            List of suggestions with confidence scores and source information
        """
        if not abbreviation:
            return []
            
        suggestions = []
        
        # Clean the abbreviation
        clean_abbr = abbreviation.strip()
        
        # 1. Try user solution dictionary lookup first (highest priority)
        if clean_abbr in self.user_solutions:
            user_solution = self.user_solutions[clean_abbr]
            suggestions.append({
                'expansion': user_solution,
                'confidence': self.confidence_scores['user_dictionary'],
                'source': 'user_dictionary'
            })
            self.stats['user_dictionary_matches'] += 1
            
            # If we have a high-confidence user-verified match, return immediately
            return suggestions
        
        # 2. Try standard dictionary lookup
        dict_suggestions = self._lookup_dictionary(clean_abbr)
        for suggestion in dict_suggestions:
            suggestions.append({
                'expansion': suggestion,
                'confidence': self.confidence_scores['dictionary'],
                'source': 'dictionary'
            })
            self.stats['dictionary_matches'] += 1
        
        # If high-confidence dictionary matches were found, skip other methods
        if suggestions and suggestions[0]['confidence'] >= 0.95:
            return suggestions[:self.suggestion_count]
        
        # 3. Try WordNet for relevant suggestions
        if self.use_wordnet and len(suggestions) < self.suggestion_count:
            wordnet_suggestions = self._consult_wordnet(clean_abbr, context_before, context_after)
            for suggestion in wordnet_suggestions:
                if suggestion not in [s['expansion'] for s in suggestions]:
                    suggestions.append({
                        'expansion': suggestion,
                        'confidence': self.confidence_scores['wordnet'],
                        'source': 'wordnet'
                    })
                    self.stats['wordnet_suggestions'] += 1
        
        # 4. Use language model if enabled and still need more suggestions
        if self.lm_enabled and len(suggestions) < self.suggestion_count:
            lm_suggestions = self._query_language_model(clean_abbr, context_before, context_after, metadata)
            for suggestion in lm_suggestions:
                if suggestion not in [s['expansion'] for s in suggestions]:
                    suggestions.append({
                        'expansion': suggestion,
                        'confidence': self.confidence_scores['language_model'],
                        'source': 'language_model'
                    })
                    self.stats['lm_suggestions'] += 1
        
        # Sort suggestions by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Update statistics
        self.stats['total_suggestions'] += len(suggestions)
        if not suggestions:
            self.stats['failed_abbreviations'] += 1
        
        return suggestions[:self.suggestion_count]
    
    def _lookup_dictionary(self, abbreviation: str) -> List[str]:
        """
        Look up an abbreviation in the dictionary.
        
        Args:
            abbreviation: Abbreviated text
            
        Returns:
            List of possible expansions
        """
        # Direct lookup
        if abbreviation in self.abbreviation_dict:
            return self.abbreviation_dict[abbreviation]
        
        # Try case-insensitive lookup
        for abbr, expansions in self.abbreviation_dict.items():
            if abbr.lower() == abbreviation.lower():
                return expansions
        
        return []
    
    def _consult_wordnet(self, abbreviation: str, context_before: str, context_after: str) -> List[str]:
        """
        Use WordNet to suggest possible expansions.
        
        Args:
            abbreviation: Abbreviated text
            context_before: Text context before the abbreviation
            context_after: Text context after the abbreviation
            
        Returns:
            List of suggested expansions from WordNet
        """
        if not NLTK_AVAILABLE or not self.use_wordnet:
            return []
            
        try:
            # Simple implementation of WordNet suggestion
            # Replace $ with n as common pattern for initial search
            cleaned_abbr = abbreviation.replace('$', 'n')
            
            # Get all words that start with the same sequence
            suggestions = []
            for synset in wordnet.synsets(cleaned_abbr[:3], lang=self.language):
                word = synset.name().split('.')[0]
                if word.startswith(cleaned_abbr[:3]) and word not in suggestions:
                    suggestions.append(word)
            
            return suggestions[:3]  # Limit to top 3
            
        except Exception as e:
            self.logger.warning(f"Error consulting WordNet: {e}")
            return []
    
    def _query_language_model(self, 
                             abbreviation: str, 
                             context_before: str, 
                             context_after: str,
                             metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Query a language model for suggestions.
        
        Args:
            abbreviation: Abbreviated text
            context_before: Text context before the abbreviation
            context_after: Text context after the abbreviation
            metadata: Optional metadata about the source
            
        Returns:
            List of suggested expansions from language model
        """
        if not self.lm_enabled:
            return []
        
        # Mock implementation for testing
        # In a real implementation, this would call an API like OpenAI
        try:
            # Mock some responses for common abbreviations
            mock_responses = {
                "co$cerning": ["concerning"],
                "lear$ed": ["learned"],
                "motiõ": ["motion"],
                "substa$tial": ["substantial"],
                "iudgme$t": ["iudgment", "judgement"],
                "argume$ts": ["arguments"],
                "co$sider": ["consider"],
                "Natu$": ["Nature"],
                "demo$strated": ["demonstrated"],
                "mai$tained": ["maintained"],
                "natu$": ["nature"]
            }
            
            if abbreviation in mock_responses:
                return mock_responses[abbreviation]
            
            # For other abbreviations, make a simple guess based on common patterns
            # even though we don't use formal pattern matching anymore
            simple_guess = abbreviation.replace('$', 'n').replace('õ', 'on')
            return [simple_guess]
            
        except Exception as e:
            self.logger.error(f"Error querying language model: {e}")
            return []
    
    def rank_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank suggestions by confidence score.
        
        Args:
            suggestions: List of suggestion dictionaries
            
        Returns:
            Ranked list of suggestions
        """
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about suggestion generation.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats