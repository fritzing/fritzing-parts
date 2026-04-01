"""Fritzing FZP and SVG validation checks package."""

# Export the main runner class and checker lists
from .fzp_checker_runner import (
    FZPCheckerRunner, 
    AVAILABLE_CHECKERS, 
    SVG_AVAILABLE_CHECKERS
)

import inspect

# Dynamically categorize checkers based on their __init__ signature
# Checkers that need SVG documents have svg_docs parameter in __init__
SVG_DEPENDENT_CHECKERS = []
FZP_ONLY_CHECKERS = []

for checker_class in AVAILABLE_CHECKERS:
    # Check if the checker's __init__ method accepts svg_docs parameter
    init_signature = inspect.signature(checker_class.__init__)
    if 'svg_docs' in init_signature.parameters:
        SVG_DEPENDENT_CHECKERS.append(checker_class)
    else:
        FZP_ONLY_CHECKERS.append(checker_class)

# Version info
__version__ = "1.0.0"