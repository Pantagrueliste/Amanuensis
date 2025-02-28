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
<<<<<<< HEAD
=======
        
        # Load legacy abbreviation dictionaries
        self._load_legacy_dictionaries()
        
        # Load common expansion patterns
        self.common_expansions = self._load_common_expansions()
        
        # Confidence scores for different sources
>>>>>>> fcb6d5e (revert to previous version)
        self.confidence_scores = {
            'dictionary': 0.9,
            'pattern': 0.4,
            'wordnet': 0.6,
            'language_model': 0.8,
            'rule_based': 0.5
        }
        
<<<<<<< HEAD
    def _load_abbreviation_dictionary(self) -> Dict[str, List[str]]:
=======
        # Statistics
        self.stats = {
            'total_suggestions': 0,
            'dictionary_matches': 0,
            'pattern_matches': 0,
            'wordnet_suggestions': 0,
            'lm_suggestions': 0,
            'failed_abbreviations': 0
        }
    
    def _load_legacy_dictionaries(self) -> None:
>>>>>>> fcb6d5e (revert to previous version)
        """
        Load legacy dictionaries from the configured paths for machine and user solutions.
        If a file isn’t available, the corresponding dictionary remains empty.
        """
<<<<<<< HEAD
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
=======
        machine_path = self.config.get('data', 'machine_solution_path', 'data/machine_solution.json')
        user_path = self.config.get('data', 'user_solution_path', 'data/user_solution.json')
        self.machine_solution_dict = {}
        self.user_solution_dict = {}

        if os.path.exists(machine_path):
            try:
                with open(machine_path, 'r', encoding='utf-8') as f:
                    self.machine_solution_dict = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading machine solution dictionary: {e}")
        else:
            self.logger.info(f"Machine solution dictionary not found at {machine_path}")

        if os.path.exists(user_path):
            try:
                with open(user_path, 'r', encoding='utf-8') as f:
                    self.user_solution_dict = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading user solution dictionary: {e}")
        else:
            self.logger.info(f"User solution dictionary not found at {user_path}")
>>>>>>> fcb6d5e (revert to previous version)
    
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
        
<<<<<<< HEAD
        # Update dictionary match stats (placeholder; actual lookup logic might be added here)
        self.stats['dictionary_matches'] += 1
                
        # 3. Try WordNet for single letter abbreviations (if no matches yet)
        if self.use_wordnet and not suggestions and len(lookup_abbr) == 1:
            wordnet_expansions = self._get_wordnet_expansions(lookup_abbr, context_before, context_after)
            
            for expansion in wordnet_expansions:
=======
        # Clean the abbreviation
        clean_abbr = abbreviation.strip()
        
        # 1. Try legacy dictionary lookup
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
>>>>>>> fcb6d5e (revert to previous version)
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['wordnet'],
                    'source': 'wordnet'
                })
            
            if wordnet_expansions:
                self.stats['wordnet_suggestions'] += 1
        
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
<<<<<<< HEAD
        Use WordNet to suggest expansions for single-letter abbreviations.
=======
        Look up an abbreviation in the legacy dictionaries.
        Checks both machine and user dictionaries separately.
>>>>>>> fcb6d5e (revert to previous version)
        
        Args:
            abbr: The abbreviated form
            context_before: Text before the abbreviation
            context_after: Text after the abbreviation
            
        Returns:
<<<<<<< HEAD
            List of possible expansions based on WordNet
        """
        try:
            # Use first letter for lookup
            letter = abbr[0].lower()
            # Search for common nouns that start with the letter
            expansions = []
=======
            List of possible expansions from the legacy sources.
        """
        suggestions = []

        # Check machine solution dictionary
        if abbreviation in self.machine_solution_dict:
            suggestions.extend(self.machine_solution_dict[abbreviation])
        else:
            for abbr, expansions in self.machine_solution_dict.items():
                if abbr.lower() == abbreviation.lower():
                    suggestions.extend(expansions)
                    break

        # Check user solution dictionary
        if abbreviation in self.user_solution_dict:
            suggestions.extend(self.user_solution_dict[abbreviation])
        else:
            for abbr, expansions in self.user_solution_dict.items():
                if abbr.lower() == abbreviation.lower():
                    suggestions.extend(expansions)
                    break

        return suggestions
    
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
            # Simple implementation of WordNet suggestion:
            # Replace $ with n as common pattern
            cleaned_abbr = abbreviation.replace('$', 'n')
>>>>>>> fcb6d5e (revert to previous version)
            
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
        
<<<<<<< HEAD
        # Placeholder - later this would call the language model service
        return []
=======
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
                "demo$strated": ["demonstrated"],
                "mai$tained": ["maintained"],
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
>>>>>>> fcb6d5e (revert to previous version)
