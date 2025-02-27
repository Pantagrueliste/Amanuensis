"""
Pytest configuration file with fixtures for Amanuensis 2.0 tests.
"""
import os
import sys
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import MagicMock

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockConfig:
    """Mock configuration class for testing."""
    
    def __init__(self, settings=None):
        self.settings = settings or {
            'xml_processing': {
                'tei_namespace': 'http://www.tei-c.org/ns/1.0',
                'abbr_xpath': '//tei:abbr',
                'expan_xpath': '//tei:expan',
                'choice_xpath': '//tei:choice',
                'context_window_size': 50,
                'include_ancestor_context': True,
                'use_choice_tags': False,
                'add_xml_ids': True
            },
            'settings': {
                'skip_expanded': False,
                'logging_level': 'INFO',
                'context_size': 20,
                'use_wordnet': True,
                'batch_size': 100,
                'language': 'eng'
            },
            'data': {
                'machine_solution_path': 'data/machine_solution.json',
                'user_solution_path': 'data/user_solution.json',
                'difficult_passages_path': 'data/difficult_passages.json',
                'unresolved_aws_path': 'data/unresolved_aw.json',
                'abbreviation_dataset_path': 'data/abbreviation_dataset.json'
            },
            'paths': {
                'input_path': 'input',
                'output_path': 'output',
                'discarded_directory': 'discarded'
            },
            'dataset': {
                'format': 'json',
                'include_metadata': True,
                'context_format': 'separate',
                'train_ratio': 0.8,
                'validation_ratio': 0.1,
                'test_ratio': 0.1,
                'stratify_by': 'abbreviated_word_length'
            },
            'language_model_integration': {
                'enabled': True,
                'provider': 'openai',
                'model_name': 'gpt-4',
                'suggestion_count': 3,
                'suggestion_temperature': 0.3,
                'request_timeout': 30,
                'max_tokens': 50,
                'batch_suggestions': False
            }
        }
    
    def get(self, section, key=None, default=None):
        """Get a configuration value."""
        try:
            if key:
                return self.settings[section][key]
            return self.settings[section]
        except KeyError:
            if default is not None:
                return default
            raise KeyError(f"Section '{section}' or key '{key}' not found in configuration file.")
    
    def get_ambiguous_aws(self):
        """Get ambiguous abbreviations."""
        return self.settings.get('ambiguity', {}).get('ambiguous_aws', [])
    
    def get_openai_integration(self, key):
        """Get OpenAI integration settings."""
        return self.settings.get('OpenAI_integration', {}).get(key)


@pytest.fixture
def mock_config():
    """Return a mock configuration object."""
    return MockConfig()


@pytest.fixture
def sample_xml_path():
    """Path to the sample XML file."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'samples', 'sampleInput.xml'))


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for output files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_abbreviations():
    """Sample abbreviation data for testing."""
    return [
        {
            "abbr_text": "co$cerning",
            "context_before": "In these latter days, we have observed the motiõ of celestial bodies with greater accuracy. The",
            "context_after": "matter of planetary orbits has been much debated among the lear$ed men of our age.",
            "metadata": {
                "title": "Sample Early Modern Text with Abbreviations",
                "author": "Anonymous",
                "date": "1650",
                "language": "eng"
            }
        },
        {
            "abbr_text": "lear$ed",
            "context_before": "The co$cerning matter of planetary orbits has been much debated among the",
            "context_after": "men of our age.",
            "metadata": {
                "title": "Sample Early Modern Text with Abbreviations",
                "author": "Anonymous",
                "date": "1650",
                "language": "eng"
            }
        },
        {
            "abbr_text": "Natu$",
            "context_before": "On the",
            "context_after": "of Light",
            "metadata": {
                "title": "Sample Early Modern Text with Abbreviations",
                "author": "Anonymous",
                "date": "1650",
                "language": "eng"
            }
        }
    ]


@pytest.fixture
def mock_openai_response():
    """Mock response from OpenAI API."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "concerning"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 25,
            "completion_tokens": 1,
            "total_tokens": 26
        }
    }