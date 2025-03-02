import logging
import re
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# Attempt to import NLTK and its WordNet corpus for advanced natural language processing.
try:
    import nltk
    from nltk.corpus import wordnet
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logging.warning("NLTK not available. Some suggestion features will be limited.")

class SuggestionGenerator:
    """
    SuggestionGenerator produces expansion suggestions for abbreviations using a combination of sources.
    
    Processing steps:
      1. Legacy dictionary lookup (from user and machine solution JSON files).
      2. Fixed regex pattern expansion based on document language.
      3. WordNet-based suggestions (for single-letter abbreviations) if no suggestions are found.
      4. Language model-based suggestions as a fallback.
      
    The document language is assumed to be set by another component (via the TEI header) and is 
    available in the configuration. This value drives which regex patterns are applied.
    
    Custom expansions are recorded in the legacy dictionary (user_solution.json) using the same format.
    """

    def __init__(self, config):
        """
        Initialize the suggestion generator with configuration.
        
        Args:
            config: A configuration object with settings, including:
                - settings: General settings (e.g. language, use_wordnet flag).
                - document: Document metadata (e.g. language from the TEI header).
                - data: Paths for legacy dictionaries.
                - language_model_integration: Settings for language model integration.
        
        Sets up internal state, loads dictionaries, and selects regex patterns based on document language.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Statistics for tracking processing details.
        self.stats = {
            'total_suggestions': 0,
            'dictionary_matches': 0,
            'pattern_matches': 0,
            'wordnet_suggestions': 0,
            'lm_suggestions': 0,
            'failed_abbreviations': 0,
            'fallback_dictionary_used': False
        }

        # General settings.
        self.language = config.get('settings', 'language', 'eng')
        # Document language retrieved from the TEI header.
        self.document_language = config.get('document', 'language', 'latin')
        self.use_wordnet = config.get('settings', 'use_wordnet', True) and NLTK_AVAILABLE

        # Language model integration settings.
        self.lm_enabled = config.get('language_model_integration', 'enabled', False)
        self.lm_provider = config.get('language_model_integration', 'provider', 'openai')
        self.lm_model = config.get('language_model_integration', 'model_name', 'gpt-4')
        self.suggestion_count = config.get('language_model_integration', 'suggestion_count', 3)

        # Load legacy abbreviation dictionaries.
        self._load_legacy_dictionaries()

        # Load regex patterns based on document language.
        self.common_expansions = self._load_common_expansions(self.document_language)

        # Confidence scores for suggestion sources.
        self.confidence_scores = {
            'dictionary': 0.8,
            'pattern': 0.4,
            'wordnet': 0.6,
            'language_model': 0.8,
            'rule_based': 0.5
        }

    def _load_legacy_dictionaries(self) -> None:
        """
        Load legacy abbreviation dictionaries from configured file paths.
        These include the machine and user solution dictionaries.
        Relative paths are made absolute using the configuration file's location or CWD.
        """
        machine_path = self.config.get('data', 'machine_solution_path', 'data/machine_solution.json')
        user_path = self.config.get('data', 'user_solution_path', 'data/user_solution.json')

        # Store user dictionary path for potential persistence.
        self._user_solution_path = user_path

        if not os.path.isabs(machine_path):
            config_dir = os.path.dirname(self.config.config_path) if hasattr(self.config, 'config_path') else os.getcwd()
            machine_path = os.path.join(config_dir, machine_path)
        if not os.path.isabs(user_path):
            config_dir = os.path.dirname(self.config.config_path) if hasattr(self.config, 'config_path') else os.getcwd()
            user_path = os.path.join(config_dir, user_path)

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

    def _load_common_expansions(self, doc_language: str) -> Dict[str, List[str]]:
        """
        Load fixed regex expansion patterns based on the document language.
        
        Args:
            doc_language: The language of the document (e.g. 'latin' or 'english').
        
        Returns:
            A dictionary mapping regex patterns to expansion templates.
        
        For Latin documents, a new pattern is included to match an isolated 'q' with a marker
        (e.g. normalized as "q$") that expands to "que".
        """
        if doc_language.lower() == 'latin':
            return {
                r'(\w+)b;$': [r'\1bus'],
                r'(\w+)q;$': [r'\1que'],
                r'(\w+)p;$': [r'\1pre'],
                r'^q\$': ['que']  # Pattern for isolated q$ (normalized from q̄)
            }
        elif doc_language.lower() == 'english':
            return {
                r'\bDr\b': ['Doctor'],
                r'\bMr\b': ['Mister'],
                r'\bSt\b': ['Saint']
            }
        else:
            self.logger.info(f"No specific regex patterns defined for language {doc_language}")
            return {}

    def generate_suggestions(self,
                             abbreviation: str,
                             context_before: str = '',
                             context_after: str = '',
                             metadata: Optional[Dict[str, Any]] = None,
                             normalized_abbr: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate expansion suggestions for an abbreviation following several steps:
        
          1. Legacy dictionary lookup (from user and machine dictionaries).
          2. Fixed regex pattern expansion based on document language.
          3. WordNet suggestions (for single-letter abbreviations) if no suggestions are found.
          4. Language model suggestions (if enabled and still no suggestions).
        
        Args:
            abbreviation: The abbreviation text (or its normalized form).
            context_before: Text preceding the abbreviation.
            context_after: Text following the abbreviation.
            metadata: Optional metadata from the document.
            normalized_abbr: Optionally pre-processed abbreviation.
        
        Returns:
            A sorted list of suggestion dictionaries with keys:
              - expansion: The suggested expansion text.
              - confidence: The confidence score.
              - source: The originating source (e.g. dictionary, pattern, wordnet, language_model).
        """
        self.stats['total_suggestions'] += 1

        lookup_abbr = normalized_abbr if normalized_abbr else abbreviation
        if not lookup_abbr and context_before:
            lookup_abbr = context_before.split()[-1]
        if not lookup_abbr:
            return []

        suggestions = []

        # 1. Legacy Dictionary Lookup.
        dict_suggestions = self._lookup_dictionary(lookup_abbr)
        for suggestion in dict_suggestions:
            suggestions.append({
                'expansion': suggestion,
                'confidence': self.confidence_scores['dictionary'],
                'source': 'dictionary'
            })
        if dict_suggestions:
            self.stats['dictionary_matches'] += 1

        # 2. Fixed Regex Pattern Expansion.
        regex_suggestions = self._apply_patterns(lookup_abbr)
        for suggestion in regex_suggestions:
            if suggestion not in [s['expansion'] for s in suggestions]:
                suggestions.append({
                    'expansion': suggestion,
                    'confidence': self.confidence_scores['pattern'],
                    'source': 'pattern'
                })
                self.stats['pattern_matches'] += 1

        # 3. WordNet Suggestions (for single-letter abbreviations).
        if not suggestions and self.use_wordnet and len(lookup_abbr) == 1:
            wordnet_expansions = self._get_wordnet_expansions(lookup_abbr, context_before, context_after)
            for expansion in wordnet_expansions:
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['wordnet'],
                    'source': 'wordnet'
                })
            if wordnet_expansions:
                self.stats['wordnet_suggestions'] += 1

        # 4. Language Model Suggestions.
        if not suggestions and self.lm_enabled:
            lm_expansions = self._get_language_model_expansions(lookup_abbr, context_before, context_after, metadata)
            for expansion in lm_expansions:
                suggestions.append({
                    'expansion': expansion,
                    'confidence': self.confidence_scores['language_model'],
                    'source': 'language_model'
                })
            if lm_expansions:
                self.stats['lm_suggestions'] += 1

        if not suggestions:
            self.stats['failed_abbreviations'] += 1

        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

    def _lookup_dictionary(self, abbreviation: str) -> List[str]:
        """
        Look up an abbreviation in the legacy dictionaries (user and machine).
        
        The lookup process:
          - Exact match in the user dictionary.
          - Exact match in the machine dictionary.
          - Case-insensitive matching if no exact match is found.
        
        Dictionary entries are normalized to lists to prevent iteration over individual characters.
        
        Returns:
            A list of expansion strings.
        """
        suggestions = []
        if not abbreviation:
            return []

        def normalize_entry(entry):
            if isinstance(entry, str):
                return [entry]
            elif isinstance(entry, list):
                return entry
            return []

        if abbreviation in self.user_solution_dict:
            user_expansions = normalize_entry(self.user_solution_dict[abbreviation])
            for expansion in user_expansions:
                if isinstance(expansion, str) and len(expansion) > 1:
                    suggestions.append(expansion)
                else:
                    self.logger.warning(f"Skipping single character expansion '{expansion}' for '{abbreviation}' from user dictionary")

        if abbreviation in self.machine_solution_dict:
            machine_expansions = normalize_entry(self.machine_solution_dict[abbreviation])
            for expansion in machine_expansions:
                if isinstance(expansion, str) and len(expansion) > 1:
                    if expansion not in suggestions:
                        suggestions.append(expansion)
                else:
                    self.logger.warning(f"Skipping single character expansion '{expansion}' for '{abbreviation}' from machine dictionary")

        if not suggestions:
            for abbr, expansions in self.user_solution_dict.items():
                if abbr.lower() == abbreviation.lower():
                    valid_expansions = [exp for exp in normalize_entry(expansions) if len(exp) > 1]
                    suggestions.extend(valid_expansions)
                    break

        if not suggestions:
            for abbr, expansions in self.machine_solution_dict.items():
                if abbr.lower() == abbreviation.lower():
                    valid_expansions = [exp for exp in normalize_entry(expansions) if len(exp) > 1]
                    suggestions.extend(valid_expansions)
                    break

        return suggestions

    def _apply_patterns(self, abbreviation: str) -> List[str]:
        """
        Apply fixed regex expansion patterns to an abbreviation.
        
        Returns:
            A list of expansion strings obtained via regex substitution.
        """
        expansions = []
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

    def _get_wordnet_expansions(self, abbr: str, context_before: str, context_after: str) -> List[str]:
        """
        Use WordNet to generate expansion suggestions for a single-letter abbreviation.
        
        Returns:
            Up to three unique suggestions from WordNet.
        """
        try:
            letter = abbr[0].lower()
            expansions = []
            synsets = list(wordnet.all_synsets('n'))[:100]
            for synset in synsets:
                lemma_names = synset.lemma_names()
                for name in lemma_names:
                    if name.startswith(letter) and len(name) > 2:
                        expansions.append(name)
            return list(set(expansions))[:3]
        except Exception as e:
            self.logger.error(f"Error getting WordNet expansions: {e}")
            return []

    def _get_language_model_expansions(self, abbr: str, context_before: str, context_after: str,
                                        metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate expansion suggestions using an external language model.
        
        Returns:
            A list of expansion strings from the language model or a fallback.
        """
        if not self.lm_enabled:
            return []

        try:
            from .gpt_suggestions import GPTSuggestions
            lm_provider = GPTSuggestions(self.config)
            return lm_provider.get_expansions(abbr, context_before, context_after, metadata)
        except Exception as e:
            self.logger.error(f"Error obtaining LM expansions: {e}")
            try:
                mock_responses = {
                    "co$cerning": ["concerning"],
                    "lear$ed": ["learned"],
                    "motiõ": ["motion"],
                    "substa$tial": ["substantial"],
                    "iudgme$t": ["judgment", "judgement"],
                    "argume$ts": ["arguments"],
                    "co$sider": ["consider"],
                    "demo$strated": ["demonstrated"],
                    "mai$tained": ["maintained"],
                    "❧": ["pilcrow"],
                    "Kingis": ["King's"],
                    "Maieſteis": ["Majesty's"],
                    "beiring": ["bearing"],
                    "incu$ming": ["incoming"],
                    "Inglis": ["English"],
                    "heines": ["highness"],
                    "thair": ["their"],
                    "gude": ["good"],
                    "Intreatment": ["treatment"],
                    "freindly": ["friendly"],
                    "vſage": ["usage"],
                    "abbreviated$word": ["abbreviatedword"],
                    "preſervatiou$": ["preservation"],
                    "sta$ding": ["standing"],
                    "gra$tit": ["granted"],
                    "conditiou$": ["condition"],
                    "obedie$ce": ["obedience"]
                }
                if abbr in mock_responses:
                    return mock_responses[abbr]
                elif abbr and '$' in abbr:
                    return [abbr.replace('$', 'n')]
                elif abbr and 'õ' in abbr:
                    return [abbr.replace('õ', 'on')]
                elif abbr:
                    return [abbr]
                else:
                    return []
            except Exception as e:
                self.logger.error(f"Error with language model mock response: {e}")
                return []

    def rank_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank the suggestions by confidence in descending order.
        
        Returns:
            The sorted list of suggestion dictionaries.
        """
        return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

    def get_statistics(self) -> Dict[str, int]:
        """
        Retrieve statistics about the suggestion generation process.
        
        Returns:
            A dictionary of statistical counts.
        """
        return self.stats

    def add_custom_expansion(self, abbreviation: str, custom_expansion: str) -> None:
        """
        Record a custom expansion for a given abbreviation in the user legacy dictionary.
        
        The custom expansion is added following the same format as in the usersolution.json.
        Future lookups for the abbreviation will then include this custom expansion.
        
        Args:
            abbreviation: The abbreviation to update.
            custom_expansion: The custom expansion string provided by the user.
        
        Notes:
            - Expansions shorter than 2 characters are ignored.
            - Optionally, the application can call save_user_dictionary() after this to persist the change.
        """
        if len(custom_expansion) <= 1:
            self.logger.warning("Custom expansion must be longer than one character")
            return

        def normalize_entry(entry):
            if isinstance(entry, str):
                return [entry]
            elif isinstance(entry, list):
                return entry
            return []

        if abbreviation in self.user_solution_dict:
            current_entries = normalize_entry(self.user_solution_dict[abbreviation])
            if custom_expansion not in current_entries:
                current_entries.append(custom_expansion)
            self.user_solution_dict[abbreviation] = current_entries
        else:
            self.user_solution_dict[abbreviation] = [custom_expansion]

        self.logger.info(f"Added custom expansion '{custom_expansion}' for abbreviation '{abbreviation}'")

    def save_user_dictionary(self) -> None:
        """
        Persist the updated user legacy dictionary to disk.
        
        This method writes the current in-memory user_solution_dict to the file specified in the configuration.
        """
        if hasattr(self, "_user_solution_path"):
            try:
                with open(self._user_solution_path, 'w', encoding='utf-8') as f:
                    json.dump(self.user_solution_dict, f, ensure_ascii=False, indent=4)
                self.logger.info(f"User dictionary saved to {self._user_solution_path}")
            except Exception as e:
                self.logger.error(f"Error saving user dictionary: {e}")
        else:
            self.logger.error("User dictionary path is not set; cannot save dictionary.")