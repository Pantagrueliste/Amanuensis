"""
Dataset Builder - Creates structured datasets from TEI abbreviations
"""

import os
import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

from ..tei.processor import AbbreviationInfo


class DatasetBuilder:
    """
    Creates formatted datasets from abbreviation data extracted from TEI documents.
    """
    
    def __init__(self, config):
        """
        Initialize the dataset builder with configuration.
        
        Args:
            config: Configuration object with dataset settings
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Dataset format settings
        self.output_format = config.get('dataset', 'format', 'json')
        self.include_metadata = config.get('dataset', 'include_metadata', True)
        self.context_format = config.get('dataset', 'context_format', 'separate')
        
        # Split settings
        self.train_ratio = config.get('dataset', 'train_ratio', 0.8)
        self.validation_ratio = config.get('dataset', 'validation_ratio', 0.1)
        self.test_ratio = config.get('dataset', 'test_ratio', 0.1)
        self.stratify_by = config.get('dataset', 'stratify_by', 'abbreviated_word_length')
        
        # LLM training format
        self.instruction_template = config.get(
            'dataset', 
            'instruction_template', 
            "Expand the abbreviation: {abbr} in context: {context}"
        )
        self.include_system_message = config.get('dataset', 'include_system_message', True)
        
        # Validation settings
        self.validate_dataset = config.get('validation', 'validate_dataset', True)
        self.min_context_length = config.get('validation', 'minimum_context_length', 20)
        self.check_duplicates = config.get('validation', 'check_duplicates', True)
        
        # Statistics
        self.stats = {
            'total_entries': 0,
            'train_entries': 0,
            'validation_entries': 0,
            'test_entries': 0,
            'skipped_entries': 0,
            'duplicate_entries': 0
        }
    
    def process_abbreviations(self, abbreviations: List[AbbreviationInfo]) -> List[Dict[str, Any]]:
        """
        Process a list of abbreviations into dataset entries.
        
        Args:
            abbreviations: List of abbreviation info objects
            
        Returns:
            List of formatted dataset entries
        """
        dataset_entries = []
        
        for abbr in abbreviations:
            entry = self._create_entry(abbr)
            if entry:
                dataset_entries.append(entry)
        
        self.stats['total_entries'] += len(dataset_entries)
        return dataset_entries
    
    def _create_entry(self, abbr: AbbreviationInfo) -> Optional[Dict[str, Any]]:
        """
        Create a dataset entry from an abbreviation.
        
        Args:
            abbr: Abbreviation info object
            
        Returns:
            Dictionary with structured data or None if invalid
        """
        # Validate context length
        if self.validate_dataset and (
            len(abbr.context_before) < self.min_context_length and 
            len(abbr.context_after) < self.min_context_length
        ):
            self.logger.warning(f"Skipping abbreviation '{abbr.abbr_text}' due to insufficient context")
            self.stats['skipped_entries'] += 1
            return None
        
        entry = {
            'abbreviation': abbr.abbr_text,
            'id': abbr.abbr_id or f"abbr_{hash(abbr.abbr_text + abbr.file_path)}"
        }
        
        # Format context based on configuration
        if self.context_format == 'separate':
            entry['context_before'] = abbr.context_before
            entry['context_after'] = abbr.context_after
        else:
            entry['context'] = f"{abbr.context_before} {abbr.abbr_text} {abbr.context_after}"
        
        # Add source information
        entry['source'] = {
            'file': abbr.file_path,
            'xpath': abbr.xpath,
            'line': abbr.line_number
        }
        
        # Include metadata if configured
        if self.include_metadata:
            entry['metadata'] = abbr.metadata
        
        return entry
    
    def split_dataset(self, entries: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split dataset into training, validation and test sets.
        
        Args:
            entries: List of dataset entries
            
        Returns:
            Tuple of (train_set, validation_set, test_set)
        """
        if not entries:
            return [], [], []
        
        # Shuffle entries deterministically for reproducibility
        random.seed(42)
        shuffled_entries = entries.copy()
        random.shuffle(shuffled_entries)
        
        # Stratify if configured
        if self.stratify_by and self.stratify_by in entries[0]:
            # Group by stratification key
            stratified_groups = {}
            for entry in shuffled_entries:
                key = entry.get(self.stratify_by, 'default')
                if key not in stratified_groups:
                    stratified_groups[key] = []
                stratified_groups[key].append(entry)
            
            # Split each group and combine
            train_set, validation_set, test_set = [], [], []
            for group in stratified_groups.values():
                t, v, ts = self._split_list(group)
                train_set.extend(t)
                validation_set.extend(v)
                test_set.extend(ts)
        else:
            # Simple split without stratification
            train_set, validation_set, test_set = self._split_list(shuffled_entries)
        
        # Update statistics
        self.stats['train_entries'] = len(train_set)
        self.stats['validation_entries'] = len(validation_set)
        self.stats['test_entries'] = len(test_set)
        
        self.logger.info(f"Split dataset: {len(train_set)} train, {len(validation_set)} validation, {len(test_set)} test")
        return train_set, validation_set, test_set
    
    def _split_list(self, items: List[Any]) -> Tuple[List[Any], List[Any], List[Any]]:
        """
        Split a list according to configured ratios.
        
        Args:
            items: List to split
            
        Returns:
            Tuple of three lists (train, validation, test)
        """
        n_items = len(items)
        n_train = int(n_items * self.train_ratio)
        n_validation = int(n_items * self.validation_ratio)
        
        train = items[:n_train]
        validation = items[n_train:n_train + n_validation]
        test = items[n_train + n_validation:]
        
        return train, validation, test
    
    def format_for_llm_training(self, entries: List[Dict[str, Any]], system_message: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Format dataset entries for LLM fine-tuning.
        
        Args:
            entries: List of dataset entries
            system_message: Optional system message for the model
            
        Returns:
            List of formatted messages for LLM training
        """
        formatted_entries = []
        
        for entry in entries:
            # Create combined context if not already present
            context = entry.get('context', '')
            if not context and ('context_before' in entry and 'context_after' in entry):
                context = f"{entry['context_before']} {entry['abbreviation']} {entry['context_after']}"
            
            # Format the prompt using the template
            instruction = self.instruction_template.format(
                abbr=entry['abbreviation'],
                context=context
            )
            
            # Structure for ChatML format
            formatted_entry = {
                "messages": []
            }
            
            # Add system message if configured
            if self.include_system_message and system_message:
                formatted_entry["messages"].append({
                    "role": "system",
                    "content": system_message
                })
            
            # Add user message with instruction
            formatted_entry["messages"].append({
                "role": "user",
                "content": instruction
            })
            
            # Add response (this would be filled with actual expansions in real data)
            # For now, just use the abbreviation as a placeholder
            formatted_entry["messages"].append({
                "role": "assistant",
                "content": entry['abbreviation'].replace('$', 'n')  # Simple placeholder
            })
            
            formatted_entries.append(formatted_entry)
        
        return formatted_entries
    
    def save_dataset(self, 
                     entries: List[Dict[str, Any]], 
                     output_path: Union[str, Path], 
                     format: Optional[str] = None) -> bool:
        """
        Save dataset to disk.
        
        Args:
            entries: List of dataset entries
            output_path: Path to save the dataset
            format: Output format (json or jsonl, defaults to configured value)
            
        Returns:
            True if successful, False otherwise
        """
        format = format or self.output_format
        
        try:
            # Convert Path to string if needed
            if isinstance(output_path, Path):
                output_path = str(output_path)
                
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if format.lower() == 'jsonl':
                with open(output_path, 'w', encoding='utf-8') as f:
                    for entry in entries:
                        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            else:
                # Default to JSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved dataset with {len(entries)} entries to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving dataset to {output_path}: {e}")
            return False
    
    def validate_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean dataset entries.
        
        Args:
            entries: List of dataset entries
            
        Returns:
            List of validated entries
        """
        if not self.validate_dataset:
            return entries
            
        valid_entries = []
        seen_ids = set()
        
        for entry in entries:
            # Check required fields
            if 'abbreviation' not in entry:
                self.logger.warning(f"Skipping entry missing 'abbreviation' field")
                self.stats['skipped_entries'] += 1
                continue
                
            # Check for duplicates
            if self.check_duplicates:
                entry_id = entry.get('id', '') 
                if entry_id in seen_ids:
                    self.logger.warning(f"Skipping duplicate entry: {entry_id}")
                    self.stats['duplicate_entries'] += 1
                    continue
                seen_ids.add(entry_id)
            
            valid_entries.append(entry)
            
        return valid_entries
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get dataset processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.stats