"""Fritzing FZP and SVG validation checks package."""

# Export the main runner class for easy import
from .fzp_checker_runner import FZPCheckerRunner

# Export commonly used checker lists
from .fzp_checker_runner import AVAILABLE_CHECKERS, SVG_AVAILABLE_CHECKERS

# Version info
__version__ = "1.0.0"