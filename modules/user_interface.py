"""
User Interface for Amanuensis 2.0 - Command Line Interface

This module provides a rich command-line interface for interacting with the Amanuensis 2.0
abbreviation expansion system.
"""

import os
import sys
import argparse
import logging
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

from .config import Config
from .tei.processor import TEIProcessor, AbbreviationInfo
from .suggestion_generator import SuggestionGenerator
from .dataset.dataset_builder import DatasetBuilder

console = Console()


class UserInterface:
    """
    Command-line interface for Amanuensis 2.0 that provides interactive 
    abbreviation expansion capabilities.
    """
    
    def __init__(self, config_path: str = "config.toml"):
        """
        Initialize the user interface.
        
        Args:
            config_path: Path to the configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config = Config(config_path)
        self.tei_processor = TEIProcessor(self.config)
        self.suggestion_generator = SuggestionGenerator(self.config)
        self.dataset_builder = DatasetBuilder(self.config)
        
        # For keeping track of user decisions
        self.user_decisions = {}
        self.abbreviations_processed = 0
        self.abbreviations_expanded = 0
        self.files_processed = 0
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _handle_interrupt(self, sig, frame):
        """Handle Ctrl+C by saving work and exiting gracefully."""
        console.print("\n[bold red]Interrupted! Saving current progress...[/bold red]")
        self._save_user_decisions()
        console.print("[bold green]Progress saved. Exiting Amanuensis 2.0[/bold green]")
        sys.exit(0)
    
    def _save_user_decisions(self):
        """Save user decisions to file and create dataset entries."""
        output_dir = Path(self.config.get("paths", "output_path"))
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw decisions first
        decisions_file = output_dir / f"user_decisions_{timestamp}.json"
        
        with open(decisions_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_decisions, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved raw user decisions to {decisions_file}")
        
        # Convert user decisions to dataset format
        dataset_entries = []
        for abbr_text, decision in self.user_decisions.items():
            entry = {
                'abbreviation': abbr_text,
                'expansion': decision['expansion'],
                'context_before': decision.get('context_before', ''),
                'context_after': decision.get('context_after', ''),
                'source': {
                    'file': decision.get('file_path', ''),
                    'confidence': decision.get('confidence', 1.0),
                    'source_type': decision.get('source', 'user')
                }
            }
            
            # Include metadata if available
            if 'metadata' in decision and decision['metadata']:
                entry['metadata'] = decision['metadata']
                
            dataset_entries.append(entry)
        
        # Save as structured dataset
        dataset_dir = output_dir / "datasets"
        dataset_dir.mkdir(exist_ok=True)
        dataset_file = dataset_dir / f"expansion_dataset_{timestamp}.json"
        
        with open(dataset_file, 'w', encoding='utf-8') as f:
            json.dump(dataset_entries, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(dataset_entries)} dataset entries to {dataset_file}")
        console.print(f"[green]Saved user decisions to {decisions_file}[/green]")
        console.print(f"[green]Created dataset with {len(dataset_entries)} entries at {dataset_file}[/green]")
    
    def show_welcome(self):
        """Display welcome message and application info."""
        title = "AMANUENSIS 2.0"
        subtitle = "Early Modern Abbreviation Expansion System"
        
        console.print(Panel.fit(
            f"[bold yellow]{title}[/bold yellow]\n[italic]{subtitle}[/italic]",
            border_style="bright_blue"
        ))
        
        console.print("\n[bold]Configuration:[/bold]")
        console.print(f"  Input path: [cyan]{self.config.get('paths', 'input_path')}[/cyan]")
        console.print(f"  Output path: [cyan]{self.config.get('paths', 'output_path')}[/cyan]")
        console.print(f"  Language model: [cyan]{self.config.get('language_model_integration', 'provider')} - {self.config.get('language_model_integration', 'model_name')}[/cyan]")
        
        console.print("\n[bold]Dataset Collection Mode:[/bold]")
        console.print("This application now runs in dataset collection mode. Instead of modifying")
        console.print("the original TEI documents, abbreviation expansions are recorded as training")
        console.print("examples for language model fine-tuning. Original documents remain unmodified.")
        
        console.print("\n[bold]Ready to collect abbreviation expansion examples.[/bold]")
    
    def show_main_menu(self) -> str:
        """
        Display the main menu and get user choice.
        
        Returns:
            User's menu choice
        """
        console.print("\n[bold]Main Menu:[/bold]")
        options = [
            "1. Extract abbreviations from TEI documents",
            "2. Interactive abbreviation expansion",
            "3. Build training dataset from collected examples",
            "4. View statistics",
            "5. Settings",
            "6. Exit"
        ]
        
        for option in options:
            console.print(f"  {option}")
        
        choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3", "4", "5", "6"])
        return choice
    
    def process_tei_documents(self):
        """Extract abbreviations from TEI documents and collect expansion examples."""
        input_path = self.config.get("paths", "input_path")
        output_path = self.config.get("paths", "output_path")
        
        # Find all XML files in the input directory
        xml_files = []
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith(".xml"):
                    xml_files.append(os.path.join(root, file))
        
        if not xml_files:
            console.print("[yellow]No XML files found in the input directory.[/yellow]")
            return
        
        console.print(f"[bold]Found {len(xml_files)} XML files to process.[/bold]")
        process_all = Confirm.ask("Process all files?")
        
        if not process_all:
            # Show file list and let user select
            table = Table(title="Available XML Files")
            table.add_column("Index", style="cyan")
            table.add_column("File Path", style="green")
            
            for idx, file_path in enumerate(xml_files, 1):
                rel_path = os.path.relpath(file_path, input_path)
                table.add_row(str(idx), rel_path)
            
            console.print(table)
            
            selected_indices = Prompt.ask(
                "Enter file numbers to process (comma-separated, e.g., 1,3,5)",
                default="1"
            )
            
            try:
                indices = [int(idx.strip()) for idx in selected_indices.split(",")]
                selected_files = [xml_files[idx-1] for idx in indices if 1 <= idx <= len(xml_files)]
            except (ValueError, IndexError):
                console.print("[bold red]Invalid selection. Using the first file.[/bold red]")
                selected_files = [xml_files[0]]
        else:
            selected_files = xml_files
        
        # Process each file
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(selected_files))
            
            for file_path in selected_files:
                rel_path = os.path.relpath(file_path, input_path)
                progress.update(task, description=f"[cyan]Processing {rel_path}...[/cyan]")
                
                # Process the file
                self._process_single_tei_file(file_path, output_path)
                
                progress.update(task, advance=1)
        
        console.print(f"[bold green]Processed {self.files_processed} files, collected {self.abbreviations_expanded} abbreviation expansions.[/bold green]")
    
    def _process_single_tei_file(self, file_path: str, output_dir: str):
        """Process a single TEI XML file."""
        try:
            # Extract abbreviations
            abbreviations, tree = self.tei_processor.parse_document(file_path)
            
            if not abbreviations:
                self.logger.info(f"No abbreviations found in {file_path}")
                return
            
            # Create output directory structure
            rel_path = os.path.relpath(file_path, self.config.get("paths", "input_path"))
            output_path = os.path.join(output_dir, rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get suggestions and record user selections without modifying documents
            expanded_count = 0
            
            use_interactive = self.config.get("user_interface", "interactive_mode", True)
            if use_interactive:
                expanded_count = self._interactive_expansion(abbreviations, tree)
            else:
                expanded_count = self._automatic_expansion(abbreviations, tree)
            
            # No need to save the document since we're no longer modifying it
            # Instead, use the dataset builder to process collected abbreviations
            # We'll handle exporting the collected data when the user chooses to save
            
            # Update statistics
            self.files_processed += 1
            self.abbreviations_expanded += expanded_count
            
            self.logger.info(f"Processed {file_path}, collected {expanded_count} abbreviation expansions")
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            console.print(f"[bold red]Error processing {file_path}: {e}[/bold red]")
    
    def _automatic_expansion(self, abbreviations: List[AbbreviationInfo], tree) -> int:
        """
        Automatically expand abbreviations using the highest confidence suggestion.
        
        Args:
            abbreviations: List of abbreviation information objects
            tree: XML tree object
            
        Returns:
            Number of abbreviations expanded
        """
        expanded_count = 0
        
        for abbr in abbreviations:
            # Generate suggestions (using normalized form for dictionary lookup)
            suggestions = self.suggestion_generator.generate_suggestions(
                "",  # Empty string as we're using normalized_form now
                "",  # Context not needed with XML-based approach
                "",  # Context not needed with XML-based approach  
                abbr.metadata,
                normalized_abbr=abbr.normalized_form  # Use normalized_form from new AbbreviationInfo
            )
            
            if not suggestions:
                continue
            
            # Use highest confidence suggestion
            best_suggestion = suggestions[0]['expansion']
            
            # Don't modify the document, just record the selection as a training example
            self.user_decisions[abbr.abbr_text] = {
                'expansion': best_suggestion,
                'context_before': abbr.context_before,
                'context_after': abbr.context_after,
                'abbreviation': abbr.abbr_text, 
                'source': suggestions[0]['source'],
                'confidence': suggestions[0]['confidence'],
                'file_path': abbr.file_path,
                'metadata': abbr.metadata
            }
            
            expanded_count += 1
        
        return expanded_count
    
    def _interactive_expansion(self, abbreviations: List[AbbreviationInfo], tree) -> int:
        """
        Interactively expand abbreviations with user input.
        
        Args:
            abbreviations: List of abbreviation information objects
            tree: XML tree object
            
        Returns:
            Number of abbreviations expanded
        """
        expanded_count = 0
        
        for i, abbr in enumerate(abbreviations, 1):
            # Get the tag name of the element without the namespace
            element_tag = abbr.abbr_element.tag.split('}')[-1] if '}' in abbr.abbr_element.tag else abbr.abbr_element.tag
            # Get element text content for display
            element_text = abbr.abbr_element.text_content() if hasattr(abbr.abbr_element, 'text_content') else "Unknown"
            
            console.print(f"\n[bold]Abbreviation {i}/{len(abbreviations)}:[/bold] [yellow]{element_text}[/yellow] (<{element_tag}> element)")
            
            # Show normalized form used for lookup
            if abbr.normalized_form:
                console.print(f"Normalized for dictionary lookup: [cyan]{abbr.normalized_form}[/cyan]")
                
            # Show XPath to locate the element
            console.print(f"Location (XPath): [dim]{abbr.xpath}[/dim]")
            
            # Generate suggestions (using normalized form for dictionary lookup)
            suggestions = self.suggestion_generator.generate_suggestions(
                "",  # Empty string as we're using normalized_form now
                "",  # Context not needed with XML-based approach
                "",  # Context not needed with XML-based approach  
                abbr.metadata,
                normalized_abbr=abbr.normalized_form  # Use normalized_form from new AbbreviationInfo
            )
            
            # Display suggestions
            table = Table(title="Expansion Suggestions")
            table.add_column("Option", style="cyan")
            table.add_column("Expansion", style="green")
            table.add_column("Confidence", style="yellow")
            table.add_column("Source", style="blue")
            
            for idx, sugg in enumerate(suggestions, 1):
                # Highlight fallback dictionary entries
                source_display = sugg['source']
                if sugg['source'] == 'dictionary' and self.suggestion_generator.stats.get('fallback_dictionary_used', False):
                    source_display = f"[yellow]{sugg['source']} (fallback)[/yellow]"
                
                table.add_row(
                    str(idx),
                    sugg['expansion'],
                    f"{sugg['confidence']:.2f}",
                    source_display
                )
            
            table.add_row("c", "Custom expansion", "-", "-")
            table.add_row("s", "Skip this abbreviation", "-", "-")
            
            console.print(table)
            
            # Get user choice
            choices = [str(i) for i in range(1, len(suggestions) + 1)] + ["c", "s"]
            choice = Prompt.ask("Select an option", choices=choices)
            
            if choice == "s":
                continue
            
            expansion = None
            if choice == "c":
                expansion = Prompt.ask("Enter custom expansion")
            else:
                idx = int(choice) - 1
                expansion = suggestions[idx]['expansion']
            
            # Determine source and confidence
            source = "custom" if choice == "c" else suggestions[int(choice)-1]['source']
            confidence = 1.0 if choice == "c" else suggestions[int(choice)-1]['confidence']
            
            self.user_decisions[abbr.abbr_text] = {
                'expansion': expansion,
                'context_before': abbr.context_before,
                'context_after': abbr.context_after,
                'abbreviation': abbr.abbr_text,
                'source': source,
                'confidence': confidence,
                'file_path': abbr.file_path,
                'metadata': abbr.metadata
            }
            
            expanded_count += 1
            
            console.print(f"[green]Recorded expansion: {expansion} (original document unchanged)[/green]")
        
        return expanded_count
    
    def build_dataset(self):
        """Build a dataset from user decisions and/or extracted abbreviations."""
        console.print("[bold]Building Dataset[/bold]")
        
        # Check if we already have user decisions to use
        if self.user_decisions:
            console.print(f"[green]Using {len(self.user_decisions)} collected abbreviation expansions.[/green]")
            
            # Convert user decisions to dataset entries
            entries = []
            for abbr_text, decision in self.user_decisions.items():
                entry = {
                    'abbreviation': abbr_text,
                    'expansion': decision['expansion'],
                    'context_before': decision.get('context_before', ''),
                    'context_after': decision.get('context_after', ''),
                    'source': {
                        'file': decision.get('file_path', ''),
                        'confidence': decision.get('confidence', 1.0),
                        'source_type': decision.get('source', 'user')
                    }
                }
                
                # Include metadata if available
                if 'metadata' in decision and decision['metadata']:
                    entry['metadata'] = decision['metadata']
                    
                entries.append(entry)
                
            console.print(f"[green]Created {len(entries)} entries from user decisions.[/green]")
        else:
            # If no user decisions, extract abbreviations from XML files
            input_path = self.config.get("paths", "input_path")
            output_path = self.config.get("paths", "output_path")
            
            # Find all XML files in the input directory
            xml_files = []
            for root, _, files in os.walk(input_path):
                for file in files:
                    if file.endswith(".xml"):
                        xml_files.append(os.path.join(root, file))
            
            if not xml_files:
                console.print("[yellow]No XML files found in the input directory.[/yellow]")
                return
            
            console.print(f"[bold]Found {len(xml_files)} XML files to process.[/bold]")
            
            # Extract abbreviations from all files
            all_abbreviations = []
            
            with Progress() as progress:
                task = progress.add_task("[cyan]Extracting abbreviations...", total=len(xml_files))
                
                for file_path in xml_files:
                    rel_path = os.path.relpath(file_path, input_path)
                    progress.update(task, description=f"[cyan]Processing {rel_path}...[/cyan]")
                    
                    # Extract abbreviations
                    abbreviations, _ = self.tei_processor.parse_document(file_path)
                    all_abbreviations.extend(abbreviations)
                    
                    progress.update(task, advance=1)
            
            console.print(f"[green]Extracted {len(all_abbreviations)} abbreviations.[/green]")
            
            # Process abbreviations into dataset entries
            entries = self.dataset_builder.process_abbreviations(all_abbreviations)
        
        # Check if we have any entries to process
        if not entries:
            console.print("[yellow]No entries to include in dataset.[/yellow]")
            return
            
        # Split dataset
        train_set, val_set, test_set = self.dataset_builder.split_dataset(entries)
        
        # Save datasets
        output_path = self.config.get("paths", "output_path")
        dataset_dir = os.path.join(output_path, "datasets")
        os.makedirs(dataset_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"expansion_dataset_{timestamp}"
        
        self.dataset_builder.save_dataset(train_set, os.path.join(dataset_dir, f"{base_filename}_train.json"))
        self.dataset_builder.save_dataset(val_set, os.path.join(dataset_dir, f"{base_filename}_validation.json"))
        self.dataset_builder.save_dataset(test_set, os.path.join(dataset_dir, f"{base_filename}_test.json"))
        
        # Format for LLM training
        system_message = self.config.get("language_model_integration", "openai", {}).get(
            "system_message", 
            "You are a linguist specializing in early modern texts. Your task is to expand abbreviated words."
        )
        
        formatted_train = self.dataset_builder.format_for_llm_training(train_set, system_message)
        self.dataset_builder.save_dataset(
            formatted_train, 
            os.path.join(dataset_dir, f"{base_filename}_train_formatted.jsonl"), 
            format="jsonl"
        )
        
        console.print(f"[bold green]Dataset creation complete![/bold green]")
        console.print(f"Train set: {len(train_set)} entries")
        console.print(f"Validation set: {len(val_set)} entries")
        console.print(f"Test set: {len(test_set)} entries")
    
    def interactive_expansion(self):
        """Interactive abbreviation expansion without document processing."""
        console.print("[bold]Interactive Abbreviation Expansion[/bold]")
        console.print("Enter abbreviations to expand them. Type 'exit' to return to the main menu.")
        
        while True:
            abbr_text = Prompt.ask("\nEnter abbreviation", default="exit")
            
            if abbr_text.lower() == 'exit':
                break
            
            context = Prompt.ask("Enter context (optional)")
            
            # Normalize the abbreviation for dictionary lookup
            normalized_abbr = None
            try:
                from modules.unicode_replacement import UnicodeReplacement
                normalized_abbr = UnicodeReplacement.normalize_abbreviation(abbr_text)
                if normalized_abbr != abbr_text:
                    console.print(f"Normalized for dictionary lookup: [cyan]{normalized_abbr}[/cyan]")
            except (ImportError, AttributeError):
                pass
            
            # Generate suggestions using normalized form if available
            suggestions = self.suggestion_generator.generate_suggestions(
                abbr_text,
                context_before=context,
                context_after="",
                normalized_abbr=normalized_abbr
            )
            
            if not suggestions:
                console.print("[yellow]No suggestions available for this abbreviation.[/yellow]")
                continue
            
            # Display suggestions
            table = Table(title=f"Suggestions for '{abbr_text}'")
            table.add_column("Expansion", style="green")
            table.add_column("Confidence", style="yellow")
            table.add_column("Source", style="blue")
            
            for sugg in suggestions:
                table.add_row(
                    sugg['expansion'],
                    f"{sugg['confidence']:.2f}",
                    sugg['source']
                )
            
            console.print(table)
    
    def show_statistics(self):
        """Display statistics about processed documents and abbreviations."""
        console.print("[bold]Statistics[/bold]")
        
        # TEI processor statistics
        tei_stats = self.tei_processor.get_statistics()
        
        table = Table(title="Processing Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Documents Processed", str(tei_stats['documents_processed']))
        table.add_row("Abbreviations Found", str(tei_stats['abbreviations_found']))
        table.add_row("Already Expanded", str(tei_stats['already_expanded']))
        table.add_row("Malformed Abbreviations", str(tei_stats['malformed_abbr']))
        table.add_row("Current Session Expansions", str(self.abbreviations_expanded))
        
        console.print(table)
        
        # Suggestion generator statistics
        sugg_stats = self.suggestion_generator.get_statistics()
        
        table = Table(title="Suggestion Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Suggestions Generated", str(sugg_stats['total_suggestions']))
        table.add_row("Dictionary Matches", str(sugg_stats['dictionary_matches']))
        table.add_row("Pattern Matches", str(sugg_stats.get('pattern_matches', 0)))
        table.add_row("WordNet Suggestions", str(sugg_stats['wordnet_suggestions']))
        table.add_row("Language Model Suggestions", str(sugg_stats['lm_suggestions']))
        table.add_row("Failed Abbreviations", str(sugg_stats['failed_abbreviations']))
        
        console.print(table)
        
        # Dataset builder statistics
        dataset_stats = self.dataset_builder.get_statistics()
        
        table = Table(title="Dataset Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Entries", str(dataset_stats['total_entries']))
        table.add_row("Training Entries", str(dataset_stats['train_entries']))
        table.add_row("Validation Entries", str(dataset_stats['validation_entries']))
        table.add_row("Test Entries", str(dataset_stats['test_entries']))
        table.add_row("Skipped Entries", str(dataset_stats['skipped_entries']))
        table.add_row("Duplicate Entries", str(dataset_stats['duplicate_entries']))
        
        console.print(table)
    
    def show_settings(self):
        """Display and modify settings."""
        console.print("[bold]Settings[/bold]")
        
        settings = {
            "User Interface": {
                "interactive_mode": self.config.get("user_interface", "interactive_mode", True),
                "show_confidence_scores": self.config.get("user_interface", "show_confidence_scores", True)
            },
            "XML Processing": {
                "use_choice_tags": self.config.get("xml_processing", "use_choice_tags", False),
                "add_xml_ids": self.config.get("xml_processing", "add_xml_ids", True),
                "skip_expanded": self.config.get("settings", "skip_expanded", False)
            },
            "Language Model": {
                "enabled": self.config.get("language_model_integration", "enabled", True),
                "provider": self.config.get("language_model_integration", "provider", "openai"),
                "model_name": self.config.get("language_model_integration", "model_name", "gpt-4")
            }
        }
        
        table = Table(title="Current Settings")
        table.add_column("Category", style="cyan")
        table.add_column("Setting", style="blue")
        table.add_column("Value", style="green")
        
        for category, category_settings in settings.items():
            for setting, value in category_settings.items():
                table.add_row(category, setting, str(value))
        
        console.print(table)
        
        # For now, just display settings without modification
        console.print("\n[yellow]Settings modification is not implemented in this version.[/yellow]")
    
    def run(self):
        """Run the main application loop."""
        self.show_welcome()
        
        while True:
            choice = self.show_main_menu()
            
            if choice == "1":
                self.process_tei_documents()
            elif choice == "2":
                self.interactive_expansion()
            elif choice == "3":
                self.build_dataset()
            elif choice == "4":
                self.show_statistics()
            elif choice == "5":
                self.show_settings()
            elif choice == "6":
                if self.user_decisions:
                    if Confirm.ask("Save your work before exiting?"):
                        self._save_user_decisions()
                console.print("[bold green]Thank you for using Amanuensis 2.0![/bold green]")
                break