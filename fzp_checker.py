#!/usr/bin/env python3
"""
Convenient wrapper for the FZP checker tool.
Usage: python fzp_checker.py [options] path
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    from scripts.checks.fzp_checker_runner import main
    main()