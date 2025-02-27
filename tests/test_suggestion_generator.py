"""
Tests for the Suggestion Generator module.
"""
import pytest
from unittest.mock import patch, MagicMock

from modules.suggestion_generator import SuggestionGenerator, NLTK_AVAILABLE


class TestSuggestionGenerator:
    """Test suite for the Suggestion Generator."""
    
    def test_init(self, mock_config):
        """Test initializing the suggestion generator."""
        generator = SuggestionGenerator(mock_config)
        
        # Check initialization of key attributes
        assert generator.language == "eng"
        assert generator.lm_enabled is True
        assert generator.lm_provider == "openai"
        assert generator.lm_model == "gpt-4"
        assert generator.suggestion_count == 3
        
        # Check confidence scores
        assert generator.confidence_scores['dictionary'] == 0.9
        assert generator.confidence_scores['pattern'] == 0.7
        assert generator.confidence_scores['language_model'] == 0.8
        
        # Check statistics initialization
        assert generator.stats['total_suggestions'] == 0
        assert generator.stats['dictionary_matches'] == 0
        assert generator.stats['lm_suggestions'] == 0
    
    def test_load_abbreviation_dictionary(self, mock_config):
        """Test loading the abbreviation dictionary."""
        generator = SuggestionGenerator(mock_config)
        
        # Dictionary should be loaded in __init__
        assert isinstance(generator.abbreviation_dict, dict)
        assert len(generator.abbreviation_dict) > 0
        
        # Check some common abbreviations
        assert "co$" in generator.abbreviation_dict
        assert "w$" in generator.abbreviation_dict
        assert "mr" in generator.abbreviation_dict
    
    def test_load_common_expansions(self, mock_config):
        """Test loading common expansion patterns."""
        generator = SuggestionGenerator(mock_config)
        
        # Patterns should be loaded in __init__
        assert isinstance(generator.common_expansions, dict)
        assert len(generator.common_expansions) > 0
        
        # Check some common patterns
        dollar_pattern = r'(\w+)\$(\w+)'
        assert dollar_pattern in generator.common_expansions
        assert len(generator.common_expansions[dollar_pattern]) == 2
    
    def test_generate_suggestions_empty(self, mock_config):
        """Test generating suggestions for empty abbreviation."""
        generator = SuggestionGenerator(mock_config)
        
        # Empty abbreviation should return empty list
        suggestions = generator.generate_suggestions("")
        assert suggestions == []
    
    def test_generate_suggestions_dictionary(self, mock_config):
        """Test generating suggestions from dictionary."""
        generator = SuggestionGenerator(mock_config)
        
        # Override dictionary for testing
        generator.abbreviation_dict = {
            "co$": ["con"],
            "mr": ["master", "mister"]
        }
        
        # Test dictionary lookup
        suggestions = generator.generate_suggestions("co$")
        assert len(suggestions) == 1
        assert suggestions[0]['expansion'] == "con"
        assert suggestions[0]['source'] == "dictionary"
        assert suggestions[0]['confidence'] == generator.confidence_scores['dictionary']
        
        # Multiple suggestions
        suggestions = generator.generate_suggestions("mr")
        assert len(suggestions) == 2
        expansions = [s['expansion'] for s in suggestions]
        assert "master" in expansions
        assert "mister" in expansions
    
    def test_generate_suggestions_pattern(self, mock_config):
        """Test generating suggestions from patterns."""
        generator = SuggestionGenerator(mock_config)
        
        # Override patterns for testing
        generator.common_expansions = {
            r'(\w+)\$(\w+)': [r'\1n\2', r'\1m\2']
        }
        
        # Empty dictionary to force pattern matching
        generator.abbreviation_dict = {}
        
        # Test pattern matching
        suggestions = generator.generate_suggestions("co$cerning")
        assert len(suggestions) == 2
        expansions = [s['expansion'] for s in suggestions]
        assert "concerning" in expansions
        assert "comcerning" in expansions
        
        # Check source and confidence
        assert suggestions[0]['source'] == "pattern"
        assert suggestions[0]['confidence'] == generator.confidence_scores['pattern']
    
    def test_generate_suggestions_wordnet(self, mock_config):
        """Test generating suggestions from WordNet."""
        generator = SuggestionGenerator(mock_config)
        
        # Mock WordNet results
        wordnet_results = ["concerned", "concert", "concord"]
        
        # Empty dictionary and patterns to force WordNet
        generator.abbreviation_dict = {}
        generator.common_expansions = {}
        
        with patch.object(generator, '_consult_wordnet', return_value=wordnet_results):
            suggestions = generator.generate_suggestions("con")
            
            # Check if suggestions were generated
            assert len(suggestions) == 3
            
            # Check source and confidence
            for suggestion in suggestions:
                assert suggestion['source'] == "wordnet"
                assert suggestion['confidence'] == generator.confidence_scores['wordnet']
            
            # Check expansions
            expansions = [s['expansion'] for s in suggestions]
            assert "concerned" in expansions
            assert "concert" in expansions
            assert "concord" in expansions
    
    def test_generate_suggestions_language_model(self, mock_config):
        """Test generating suggestions from language model."""
        generator = SuggestionGenerator(mock_config)
        
        # Set up language model configuration
        generator.lm_enabled = True
        
        # Empty other sources to force language model
        generator.abbreviation_dict = {}
        generator.common_expansions = {}
        
        with patch.object(generator, '_consult_wordnet', return_value=[]):
            with patch.object(generator, '_query_language_model', return_value=["concerning"]):
                suggestions = generator.generate_suggestions("co$cerning")
                
                # Check if suggestions were generated
                assert len(suggestions) == 1
                
                # Check source and confidence
                assert suggestions[0]['source'] == "language_model"
                assert suggestions[0]['confidence'] == generator.confidence_scores['language_model']
                assert suggestions[0]['expansion'] == "concerning"
    
    def test_lookup_dictionary(self, mock_config):
        """Test dictionary lookup function."""
        generator = SuggestionGenerator(mock_config)
        
        # Set up test dictionary
        generator.abbreviation_dict = {
            "co$": ["con"],
            "Mr": ["Master", "Mister"]
        }
        
        # Test direct lookup
        assert generator._lookup_dictionary("co$") == ["con"]
        
        # Test case-insensitive lookup
        assert generator._lookup_dictionary("mr") == ["Master", "Mister"]
        
        # Test non-existent abbreviation
        assert generator._lookup_dictionary("xyz") == []
    
    def test_apply_patterns(self, mock_config):
        """Test pattern application function."""
        generator = SuggestionGenerator(mock_config)
        
        # Set up test patterns
        generator.common_expansions = {
            r'(\w+)\$(\w+)': [r'\1n\2', r'\1m\2'],
            r'(\w+)õ$': [r'\1on', r'\1om']
        }
        
        # Test dollar sign pattern
        expansions = generator._apply_patterns("co$cerning")
        assert "concerning" in expansions
        assert "comcerning" in expansions
        
        # Test tilde pattern
        expansions = generator._apply_patterns("motiõ")
        assert "motion" in expansions
        assert "motiom" in expansions
        
        # Test non-matching pattern
        assert generator._apply_patterns("normal") == []
    
    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not available")
    def test_consult_wordnet(self, mock_config):
        """Test WordNet consultation function."""
        generator = SuggestionGenerator(mock_config)
        generator.use_wordnet = True
        
        # Mock wordnet.synsets
        synset_mock = MagicMock()
        synset_mock.name.return_value = "concerned.v.01"
        
        with patch('nltk.corpus.wordnet.synsets', return_value=[synset_mock]):
            suggestions = generator._consult_wordnet("con", "before", "after")
            
            # Should return the mocked synset name
            assert len(suggestions) > 0
            assert "concerned" in suggestions
    
    def test_query_language_model(self, mock_config):
        """Test language model query function."""
        generator = SuggestionGenerator(mock_config)
        generator.lm_enabled = True
        
        # Test with known abbreviation
        suggestions = generator._query_language_model("co$cerning", "before", "after")
        assert suggestions == ["concerning"]
        
        # Test with unknown abbreviation
        suggestions = generator._query_language_model("te$ting", "before", "after")
        assert suggestions == ["tenting"]
    
    def test_rank_suggestions(self, mock_config):
        """Test suggestion ranking function."""
        generator = SuggestionGenerator(mock_config)
        
        # Create test suggestions
        suggestions = [
            {'expansion': 'first', 'confidence': 0.5, 'source': 'test'},
            {'expansion': 'second', 'confidence': 0.9, 'source': 'test'},
            {'expansion': 'third', 'confidence': 0.7, 'source': 'test'}
        ]
        
        # Rank suggestions
        ranked = generator.rank_suggestions(suggestions)
        
        # Check ranking
        assert ranked[0]['expansion'] == 'second'  # Highest confidence
        assert ranked[1]['expansion'] == 'third'   # Medium confidence
        assert ranked[2]['expansion'] == 'first'   # Lowest confidence
    
    def test_get_statistics(self, mock_config):
        """Test statistics retrieval."""
        generator = SuggestionGenerator(mock_config)
        
        # Set some statistics
        generator.stats['total_suggestions'] = 10
        generator.stats['dictionary_matches'] = 5
        generator.stats['pattern_matches'] = 3
        generator.stats['lm_suggestions'] = 2
        
        # Get statistics
        stats = generator.get_statistics()
        
        # Check statistics
        assert stats['total_suggestions'] == 10
        assert stats['dictionary_matches'] == 5
        assert stats['pattern_matches'] == 3
        assert stats['lm_suggestions'] == 2