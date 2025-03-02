import os
import importlib
from fzp_checkers import FZPChecker

# Will hold all discovered FZP checkers
additional_fzp_checkers = []

# Auto-import when module is loaded
fzp_dir = os.path.join(os.path.dirname(__file__), 'fzp')
for file in os.listdir(fzp_dir):
    if file.endswith('.py'):
        module_name = file[:-3]
        module = importlib.import_module(f'.fzp.{module_name}', package=__package__)
        for name, item in module.__dict__.items():
            if (isinstance(item, type) and
                issubclass(item, FZPChecker) and
                item != FZPChecker):
                globals()[name] = item  # Makes checker available for import
                additional_fzp_checkers.append(item)  # Adds to list for AVAILABLE_CHECKERS
