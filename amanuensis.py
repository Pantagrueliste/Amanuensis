#!/usr/bin/env python3
"""
Amanuensis 2.0 Launcher

This script is the entry point for the Amanuensis 2.0 application.
It sets up the necessary environment and launches the main application.
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure the modules directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from modules.main import main


if __name__ == "__main__":
    # Launch the application
    main()