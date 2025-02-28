import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.tei.processor import TEIProcessor
from modules.config import Config


class MockConfig:
    def __init__(self, config_dict=None):
        self.config_dict = config_dict or {}
        
    def get(self, section, key, default=None):
        if section in self.config_dict and key in self.config_dict[section]:
            return self.config_dict[section][key]
        return default


def test_normalize_specific_abbreviation():
    """Test the normalization of a specific abbreviation."""
    config = MockConfig({
        'settings': {
            'normalize_abbreviations': True
        },
        'xml_processing': {
            'tei_namespace': 'http://www.tei-c.org/ns/1.0',
            'abbr_xpath': '//tei:abbr',
            'expan_xpath': '//tei:expan',
            'choice_xpath': '//tei:choice'
        }
    })
    
    processor = TEIProcessor(config)
    
    # Test with the specific example
    abbr_text = 'Eleophyllu<g ref="char:cmbAbbrStroke">̄</g>'
    normalized = processor._normalize_abbreviation(abbr_text)
    
    print(f"Original: {abbr_text}")
    print(f"Normalized: {normalized}")
    
    # Should be "Eleophyllu$"
    assert normalized == "Eleophyllu$"
    
    print("Test passed!")


if __name__ == "__main__":
    test_normalize_specific_abbreviation()