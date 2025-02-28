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
        
        # Statistics
        self.stats = {
            'total_suggestions': 0,
            'user_dictionary_matches': 0,
            'dictionary_matches': 0,
            'wordnet_suggestions': 0,
            'lm_suggestions': 0,
            'failed_abbreviations': 0,
            'fallback_dictionary_used': False  # Track if fallback dictionary was used
        }
        
        # Load settings
        self.language = config.get('settings', 'language', 'eng')
        self.use_wordnet = config.get('settings', 'use_wordnet', True) and NLTK_AVAILABLE
        
        # Load language model settings
        self.lm_enabled = config.get('language_model_integration', 'enabled', False)
        self.lm_provider = config.get('language_model_integration', 'provider', 'openai')
        self.lm_model = config.get('language_model_integration', 'model_name', 'gpt-4')
        self.suggestion_count = config.get('language_model_integration', 'suggestion_count', 3)
        
        # Confidence scores for different sources - prioritizing dictionaries
        self.confidence_scores = {
            'user_dictionary': 0.98,   # Highest confidence for user-verified solutions
            'dictionary': 0.95,        # Very high confidence for standard dictionary
            'language_model': 0.8,     # High confidence for LLM suggestions
            'wordnet': 0.5,            # Lower confidence for wordnet
            'rule_based': 0.4          # Lowest confidence
        }
        
        # Set up expansion sources
        self.abbreviation_dict = self._load_abbreviation_dictionary()
        self.user_solutions = self._load_user_solutions()
    
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
            self.stats['fallback_dictionary_used'] = True
            self.logger.warning("Using fallback abbreviation dictionary")
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
            self.stats['fallback_dictionary_used'] = True
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
                             metadata: Optional[Dict[str, Any]] = None,
                             normalized_abbr: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate expansion suggestions for an abbreviation.
        
        Args:
            abbreviation: The abbreviation text or normalized form
            context_before: Optional context before the abbreviation (may be empty with XML-based approach)
            context_after: Optional context after the abbreviation (may be empty with XML-based approach)
            metadata: Optional document metadata
            normalized_abbr: Optional normalized form of the abbreviation (preferred over abbreviation)
            
        Returns:
            List of suggestions sorted by confidence
        """
        if not abbreviation:
            return []
        
        # Track attempts
        self.stats['total_suggestions'] += 1
        
        # Use normalized form if provided
        lookup_abbr = normalized_abbr if normalized_abbr else abbreviation
        
        # Initialize suggestions list
        suggestions = []
        
        # 1. Check user-verified solutions (highest priority)
        if lookup_abbr in self.user_solutions:
            expansion = self.user_solutions[lookup_abbr]
            suggestions.append({
                'expansion': expansion,
                'confidence': self.confidence_scores['user_dictionary'],
                'source': 'user_dictionary'
            })
            self.stats['user_dictionary_matches'] += 1
        
        # 2. Check dictionary of standard abbreviations
        if lookup_abbr in self.abbreviation_dict:
            expansions = self.abbreviation_dict[lookup_abbr]
            for expansion in expansions:
                # Skip duplicates
                if any(s['expansion'] == expansion for s in suggestions):
                    continue
                
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['dictionary'],
                    'source': 'dictionary'
                })
            self.stats['dictionary_matches'] += 1
                
        # 3. Try WordNet for single letter abbreviations (if no matches yet)
        if self.use_wordnet and not suggestions and len(lookup_abbr) == 1:
            wordnet_expansions = self._get_wordnet_expansions(lookup_abbr, context_before, context_after)
            
            for expansion in wordnet_expansions:
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['wordnet'],
                    'source': 'wordnet'
                })
            
            if wordnet_expansions:
                self.stats['wordnet_suggestions'] += 1
        
        # 4. Use language model if enabled and no matches yet
        if self.lm_enabled and not suggestions:
            lm_expansions = self._get_language_model_expansions(
                lookup_abbr, context_before, context_after, metadata
            )
            
            for expansion in lm_expansions:
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['language_model'],
                    'source': 'language_model'
                })
            
            if lm_expansions:
                self.stats['lm_suggestions'] += 1
        
        # Track failures
        if not suggestions:
            self.stats['failed_abbreviations'] += 1
            
        # Sort by confidence (highest first)
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def _get_wordnet_expansions(self, 
                               abbr: str, 
                               context_before: str, 
                               context_after: str) -> List[str]:
        """
        Use WordNet to suggest expansions for single-letter abbreviations.
        
        Args:
            abbr: The abbreviated form
            context_before: Text before the abbreviation
            context_after: Text after the abbreviation
            
        Returns:
            List of possible expansions based on WordNet
        """
        if not NLTK_AVAILABLE or len(abbr) != 1:
            return []
        
        try:
            # For single letters, try to find words that start with that letter
            letter = abbr[0].lower()
            
            # Search for common nouns that start with the letter
            expansions = []
            
            for synset in wordnet.all_synsets('n')[:100]:  # Limit to first 100 noun synsets for performance
                lemma_names = synset.lemma_names()
                for name in lemma_names:
                    if name.startswith(letter) and len(name) > 2:  # Skip very short words
                        expansions.append(name)
            
            # Return the most common options (limited)
            return list(set(expansions))[:3]
            
        except Exception as e:
            self.logger.error(f"Error getting WordNet expansions: {e}")
            return []
    
    def _get_language_model_expansions(self, 
                                      abbr: str, 
                                      context_before: str, 
                                      context_after: str,
                                      metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Use language model to suggest expansions.
        
        Args:
            abbr: The abbreviated form
            context_before: Text before the abbreviation
            context_after: Text after the abbreviation
            metadata: Optional metadata about the source
            
        Returns:
            List of possible expansions based on language model
        """
        if not self.lm_enabled:
            return []
        
        # For now, use a placeholder since this will be implemented
        # in the language model integration module
        self.logger.info(f"Language model would be used for: {abbr}")
        
        # Placeholder - later this would call the language model service
        return []