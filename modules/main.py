"""
Amanuensis 2.0 - Early Modern Abbreviation Expansion System

This application processes TEI XML documents containing early modern abbreviations
and provides tools for expanding those abbreviations using various methods.

Features:
- TEI XML processing with abbreviation identification and extraction
- Multiple suggestion methods: dictionaries, patterns, WordNet, language models
- Interactive and automatic expansion modes
- Dataset creation for training language models
- Rich command-line interface with configuration options
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import signal

from .config import Config
from .logging_config import setup_logging
from .user_interface import UserInterface
from .tei.processor import TEIProcessor
from .suggestion_generator import SuggestionGenerator
from .dataset.dataset_builder import DatasetBuilder


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Amanuensis 2.0 - Early Modern Abbreviation Expansion System"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.toml",
        help="Path to configuration file (default: config.toml)"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input directory containing TEI XML files (overrides config file)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for processed files (overrides config file)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Run in non-interactive mode with default settings"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--process", "-p",
        type=str,
        help="Process a specific TEI XML file"
    )
    
    return parser.parse_args()


def check_environment():
    """Check if the environment is properly configured."""
    if os.getenv('OPENAI_API_KEY') is None:
        print("Warning: OpenAI API key not found in environment variables.")
        print("Some suggestion features may be limited.")
        return False
    return True


def main():
    """Main entry point for Amanuensis 2.0."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Check environment
    env_ok = check_environment()
    
    try:
        # Create UI
        ui = UserInterface(args.config)
        
        # Override config with command line arguments if provided
        if args.input:
            ui.config.settings["paths"]["input_path"] = args.input
        
        if args.output:
            ui.config.settings["paths"]["output_path"] = args.output
        
        # Process a specific file if requested
        if args.process:
            if not os.path.exists(args.process):
                logger.error(f"File not found: {args.process}")
                sys.exit(1)
                
            if args.quiet:
                # Non-interactive mode
                output_dir = ui.config.get("paths", "output_path")
                
                # Process file
                processor = TEIProcessor(ui.config)
                suggestion_generator = SuggestionGenerator(ui.config)
                
                # Extract abbreviations
                abbreviations, tree = processor.parse_document(args.process)
                
                # Process each abbreviation
                expanded_count = 0
                for abbr in abbreviations:
                    # Generate suggestions (using normalized form if available)
                    suggestions = suggestion_generator.generate_suggestions(
                        abbr.normalized_form or "",  # Use normalized form for lookup
                        "",  # Context is not needed with the new approach
                        "",  # Context is not needed with the new approach
                        abbr.metadata,
                        normalized_abbr=abbr.normalized_form
                    )
                    
                    if suggestions:
                        # Use highest confidence suggestion
                        expansion = suggestions[0]['expansion']
                        if processor.add_expansion(abbr, expansion):
                            expanded_count += 1
                
                # Save the modified document
                output_path = os.path.join(output_dir, os.path.basename(args.process))
                processor.save_document(tree, output_path)
                
                print(f"Processed {args.process} with {expanded_count} expansions.")
                print(f"Output saved to {output_path}")
                
            else:
                # Interactive mode for single file
                output_dir = ui.config.get("paths", "output_path")
                ui._process_single_tei_file(args.process, output_dir)
        else:
            # Run the UI main loop
            ui.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        print("\nExiting Amanuensis 2.0")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
