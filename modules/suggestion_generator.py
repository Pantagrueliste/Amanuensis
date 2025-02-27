"""
Suggestion Generator - Generates expansion suggestions for abbreviations
"""

import logging
import re
import os
import json
import importlib.resources
from typing import List, Dict, Any, Optional, Tuple, Union
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
    Generates expansion suggestions for abbreviations using various methods.
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
        self.common_expansions = self._load_common_expansions()
        
        # Confidence scores for different sources
        self.confidence_scores = {
            'dictionary': 0.9,
            'pattern': 0.7,
            'wordnet': 0.6,
            'language_model': 0.8,
            'rule_based': 0.5
        }
        
        # Statistics
        self.stats = {
            'total_suggestions': 0,
            'dictionary_matches': 0,
            'pattern_matches': 0,
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
    
    def _load_common_expansions(self) -> Dict[str, List[str]]:
        """
        Load common expansion patterns.
        
        Returns:
            Dictionary of pattern regex to expansion templates
        """
        return {
            # Dollar sign as medial n/m
            r'(\w+)\$(\w+)': [r'\1n\2', r'\1m\2'],
            
            # Tilde as final n/m
            r'(\w+)õ$': [r'\1on', r'\1om'],
            r'(\w+)ã$': [r'\1an', r'\1am'],
            r'(\w+)ẽ$': [r'\1en', r'\1em'],
            
            # Superscript abbreviations
            r'(\w+)r$': [r'\1er', r'\1or'],
            r'(\w+)d$': [r'\1ed'],
            r'(\w+)t$': [r'\1th', r'\1et'],
            
            # Common Latin abbreviations
            r'(\w+)b;$': [r'\1bus'],
            r'(\w+)q;$': [r'\1que'],
            r'(\w+)p;$': [r'\1pre']
        }
    
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
        
        # 1. Try dictionary lookup
        dict_suggestions = self._lookup_dictionary(clean_abbr)
        for suggestion in dict_suggestions:
            suggestions.append({
                'expansion': suggestion,
                'confidence': self.confidence_scores['dictionary'],
                'source': 'dictionary'
            })
            self.stats['dictionary_matches'] += 1
        
        # 2. Try pattern-based expansions
        pattern_suggestions = self._apply_patterns(clean_abbr)
        for suggestion in pattern_suggestions:
            if suggestion not in [s['expansion'] for s in suggestions]:
                suggestions.append({
                    'expansion': suggestion,
                    'confidence': self.confidence_scores['pattern'],
                    'source': 'pattern'
                })
                self.stats['pattern_matches'] += 1
        
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
    
    def _apply_patterns(self, abbreviation: str) -> List[str]:
        """
        Apply expansion patterns to an abbreviation.
        
        Args:
            abbreviation: Abbreviated text
            
        Returns:
            List of expansions based on patterns
        """
        expansions = []
        
        # Apply each pattern
        for pattern, templates in self.common_expansions.items():
            match = re.match(pattern, abbreviation)
            if match:
                for template in templates:
                    try:
                        expansion = re.sub(pattern, template, abbreviation)
                        expansions.append(expansion)
                    except Exception as e:
                        self.logger.warning(f"Error applying pattern {pattern} to {abbreviation}: {e}")
        
        return expansions
    
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
            # Replace $ with n as common pattern
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
            
            # For other abbreviations, make a simple guess
            return [abbreviation.replace('$', 'n').replace('õ', 'on')]
            
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