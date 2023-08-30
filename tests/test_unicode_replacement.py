import sys
import unittest
from unittest import TestCase

sys.path.append("/Users/clem/GitHub/Amanuensis")
from modules.unicode_replacement import UnicodeReplacement

class MockConfig:
    def get(self, section, key):
        mock_data = {
            'unicode_replacements': {
                'replacements_on': True,
                'characters_to_delete': ['a'],
                'characters_to_replace': {'b': 'c'}
            },
            'paths': {
                'output_path': '/tests/output'
            }
        }
        return mock_data.get(section, {}).get(key)

class TestUnicodeReplacement(unittest.TestCase):
    def test_initialization(self):
        mock_config = MockConfig()
        ur_instance = UnicodeReplacement(mock_config)

if __name__ == '__main__':
    unittest.main()
