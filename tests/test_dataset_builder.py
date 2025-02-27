"""
Tests for the Dataset Builder module.
"""
import os
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

# Create __init__.py in the dataset directory to make it importable
from modules.dataset.dataset_builder import DatasetBuilder
from modules.tei.processor import AbbreviationInfo


class TestDatasetBuilder:
    """Test suite for the Dataset Builder."""
    
    def test_init(self, mock_config):
        """Test initializing the dataset builder."""
        builder = DatasetBuilder(mock_config)
        
        # Check initialization of key attributes
        assert builder.output_format == "json"
        assert builder.include_metadata is True
        assert builder.context_format == "separate"
        assert builder.train_ratio == 0.8
        assert builder.validation_ratio == 0.1
        assert builder.test_ratio == 0.1
        assert builder.validate_dataset is True
        
        # Check statistics initialization
        assert builder.stats['total_entries'] == 0
        assert builder.stats['train_entries'] == 0
        assert builder.stats['validation_entries'] == 0
        assert builder.stats['test_entries'] == 0
        assert builder.stats['skipped_entries'] == 0
        assert builder.stats['duplicate_entries'] == 0
    
    def test_process_abbreviations(self, mock_config):
        """Test processing abbreviations into dataset entries."""
        builder = DatasetBuilder(mock_config)
        
        # Create mock abbreviations
        abbreviations = [
            AbbreviationInfo(
                abbr_text="co$cerning",
                abbr_id="abbr_1",
                abbr_element=MagicMock(),
                parent_element=MagicMock(),
                context_before="In these latter days, we have observed the motiõ of celestial bodies with greater accuracy. The",
                context_after="matter of planetary orbits has been much debated among the lear$ed men of our age.",
                file_path="/test/file1.xml",
                line_number=10,
                xpath="/TEI/text/body/div/p/abbr[1]",
                metadata={"title": "Test Document", "author": "Test Author"}
            ),
            AbbreviationInfo(
                abbr_text="lear$ed",
                abbr_id="abbr_2",
                abbr_element=MagicMock(),
                parent_element=MagicMock(),
                context_before="The co$cerning matter of planetary orbits has been much debated among the",
                context_after="men of our age.",
                file_path="/test/file1.xml",
                line_number=12,
                xpath="/TEI/text/body/div/p/abbr[2]",
                metadata={"title": "Test Document", "author": "Test Author"}
            )
        ]
        
        # Process abbreviations
        entries = builder.process_abbreviations(abbreviations)
        
        # Check results
        assert len(entries) == 2
        assert entries[0]['abbreviation'] == "co$cerning"
        assert entries[0]['id'] == "abbr_1"
        assert entries[0]['context_before'] == abbreviations[0].context_before
        assert entries[0]['context_after'] == abbreviations[0].context_after
        assert entries[0]['source']['file'] == "/test/file1.xml"
        assert entries[0]['metadata']['title'] == "Test Document"
        
        # Check statistics
        assert builder.stats['total_entries'] == 2
    
    def test_create_entry_with_insufficient_context(self, mock_config):
        """Test handling abbreviations with insufficient context."""
        builder = DatasetBuilder(mock_config)
        builder.min_context_length = 30  # Set higher than actual context
        
        # Create abbreviation with short context
        abbr = AbbreviationInfo(
            abbr_text="co$cerning",
            abbr_id="abbr_1",
            abbr_element=MagicMock(),
            parent_element=MagicMock(),
            context_before="Short context",
            context_after="Also short",
            file_path="/test/file1.xml",
            line_number=10,
            xpath="/TEI/text/body/div/p/abbr[1]",
            metadata={"title": "Test Document"}
        )
        
        # Create entry
        entry = builder._create_entry(abbr)
        
        # Check that entry was skipped
        assert entry is None
        assert builder.stats['skipped_entries'] == 1
    
    def test_create_entry_with_combined_context(self, mock_config):
        """Test creating entries with combined context format."""
        builder = DatasetBuilder(mock_config)
        builder.context_format = "combined"
        
        # Create abbreviation
        abbr = AbbreviationInfo(
            abbr_text="co$cerning",
            abbr_id="abbr_1",
            abbr_element=MagicMock(),
            parent_element=MagicMock(),
            context_before="Context before",
            context_after="Context after",
            file_path="/test/file1.xml",
            line_number=10,
            xpath="/TEI/text/body/div/p/abbr[1]",
            metadata={"title": "Test Document"}
        )
        
        # Create entry
        entry = builder._create_entry(abbr)
        
        # Check that context was combined
        assert 'context' in entry
        assert entry['context'] == "Context before co$cerning Context after"
        assert 'context_before' not in entry
        assert 'context_after' not in entry
    
    def test_split_dataset(self, mock_config):
        """Test splitting dataset into train/val/test sets."""
        builder = DatasetBuilder(mock_config)
        
        # Create sample entries
        entries = [
            {'id': f'entry_{i}', 'abbreviation': f'abbr_{i}'} 
            for i in range(100)
        ]
        
        # Split dataset
        train, val, test = builder.split_dataset(entries)
        
        # Check split ratios
        assert len(train) == 80
        assert len(val) == 10
        assert len(test) == 10
        
        # Check statistics
        assert builder.stats['train_entries'] == 80
        assert builder.stats['validation_entries'] == 10
        assert builder.stats['test_entries'] == 10
        
        # Check that all entries are included
        all_ids = set(e['id'] for e in train + val + test)
        assert len(all_ids) == 100
    
    def test_split_empty_dataset(self, mock_config):
        """Test splitting an empty dataset."""
        builder = DatasetBuilder(mock_config)
        
        # Split empty dataset
        train, val, test = builder.split_dataset([])
        
        # Check results
        assert len(train) == 0
        assert len(val) == 0
        assert len(test) == 0
    
    def test_format_for_llm_training(self, mock_config):
        """Test formatting entries for LLM training."""
        builder = DatasetBuilder(mock_config)
        
        # Create sample entries
        entries = [
            {
                'id': 'entry_1',
                'abbreviation': 'co$cerning',
                'context_before': 'Context before',
                'context_after': 'Context after'
            },
            {
                'id': 'entry_2',
                'abbreviation': 'argume$t',
                'context': 'Full context with argume$t inside'
            }
        ]
        
        # Format entries
        system_message = "You are a linguist specializing in early modern texts."
        formatted = builder.format_for_llm_training(entries, system_message)
        
        # Check results
        assert len(formatted) == 2
        
        # Check first entry
        assert len(formatted[0]['messages']) == 3
        assert formatted[0]['messages'][0]['role'] == 'system'
        assert formatted[0]['messages'][0]['content'] == system_message
        assert formatted[0]['messages'][1]['role'] == 'user'
        assert 'co$cerning' in formatted[0]['messages'][1]['content']
        assert formatted[0]['messages'][2]['role'] == 'assistant'
        assert formatted[0]['messages'][2]['content'] == 'concerning'
        
        # Check second entry with pre-combined context
        assert 'argume$t' in formatted[1]['messages'][1]['content']
        assert formatted[1]['messages'][2]['content'] == 'argument'
    
    def test_save_dataset_json(self, mock_config, temp_output_dir):
        """Test saving dataset in JSON format."""
        builder = DatasetBuilder(mock_config)
        
        # Create sample entries
        entries = [
            {'id': 'entry_1', 'abbreviation': 'co$cerning'},
            {'id': 'entry_2', 'abbreviation': 'lear$ed'}
        ]
        
        # Save dataset
        output_path = os.path.join(temp_output_dir, "test_dataset.json")
        result = builder.save_dataset(entries, output_path)
        
        # Check result
        assert result is True
        assert os.path.exists(output_path)
        
        # Verify file contents
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert len(saved_data) == 2
            assert saved_data[0]['id'] == 'entry_1'
            assert saved_data[1]['abbreviation'] == 'lear$ed'
    
    def test_save_dataset_jsonl(self, mock_config, temp_output_dir):
        """Test saving dataset in JSONL format."""
        builder = DatasetBuilder(mock_config)
        
        # Create sample entries
        entries = [
            {'id': 'entry_1', 'abbreviation': 'co$cerning'},
            {'id': 'entry_2', 'abbreviation': 'lear$ed'}
        ]
        
        # Save dataset
        output_path = os.path.join(temp_output_dir, "test_dataset.jsonl")
        result = builder.save_dataset(entries, output_path, format='jsonl')
        
        # Check result
        assert result is True
        assert os.path.exists(output_path)
        
        # Verify file contents
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            line1_data = json.loads(lines[0])
            line2_data = json.loads(lines[1])
            
            assert line1_data['id'] == 'entry_1'
            assert line2_data['abbreviation'] == 'lear$ed'
    
    def test_validate_entries(self, mock_config):
        """Test validating dataset entries."""
        builder = DatasetBuilder(mock_config)
        builder.validate_dataset = True
        builder.check_duplicates = True
        
        # Create sample entries including invalid ones
        entries = [
            {'id': 'entry_1', 'abbreviation': 'co$cerning'},
            {'id': 'entry_1', 'abbreviation': 'duplicate_id'},  # Duplicate ID
            {'abbreviation': 'no_id'},  # No ID
            {'id': 'entry_3'}  # No abbreviation
        ]
        
        # Validate entries
        valid_entries = builder.validate_entries(entries)
        
        # Check results
        assert len(valid_entries) == 2  # Only valid entries remain
        assert valid_entries[0]['id'] == 'entry_1'
        assert valid_entries[1]['abbreviation'] == 'no_id'
        
        # Check statistics
        assert builder.stats['duplicate_entries'] == 1
        assert builder.stats['skipped_entries'] == 1
    
    def test_get_statistics(self, mock_config):
        """Test getting dataset statistics."""
        builder = DatasetBuilder(mock_config)
        
        # Set some statistics
        builder.stats['total_entries'] = 100
        builder.stats['train_entries'] = 80
        builder.stats['validation_entries'] = 10
        builder.stats['test_entries'] = 10
        builder.stats['skipped_entries'] = 5
        
        # Get statistics
        stats = builder.get_statistics()
        
        # Check results
        assert stats['total_entries'] == 100
        assert stats['train_entries'] == 80
        assert stats['validation_entries'] == 10
        assert stats['test_entries'] == 10
        assert stats['skipped_entries'] == 5