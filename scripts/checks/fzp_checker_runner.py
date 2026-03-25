from lxml import etree
from .fzp_checkers import *
from .check_missing_leg_ids import *
from .connector_numbering import *
from .svg_checkers import *
from .fzp_svg_checkers import FZPMissingConnectorRefsChecker
from .fzp_checkers import ValidationIssue
from .fzp_utils import FZPUtils
import json
import re
import os
import sys
import logging

class FZPCheckerRunner:
    def __init__(self, path):
        self.path = path
        self.total_errors = 0
        self.total_warnings = 0
        self.extracted_dir = None  # For fzpz cleanup
        self.checks_run = 0
        self.errors_fixed = 0
        self.logger = logging.getLogger(self.__class__.__name__)
        self.all_issues = []  # ValidationIssue objects from FZP checks
        self.all_fixes = []   # FixResult objects from FZP checks
        self.svg_file_results = {}  # SVG file path -> {'issues': [], 'fixes': []}

    def check(self, check_types, svg_check_types, fix=False):
        self.total_errors = 0
        self.total_warnings = 0
        self.checks_run = 0
        self.errors_fixed = 0
        self.all_issues = []
        self.all_fixes = []
        self.svg_file_results = {}
        
        # Handle fzpz files
        original_path = self.path
        if self.path.endswith('.fzpz'):
            self.path = FZPUtils.extract_fzpz(self.path)
            self.extracted_dir = os.path.dirname(self.path)
            self.logger.debug(f"Extracted FZPZ to: {self.extracted_dir}")
            # Debug: list extracted files
            extracted_files = os.listdir(self.extracted_dir)
            self.logger.debug(f"Extracted files: {extracted_files}")
        
        try:
            fzp_doc = self._parse_fzp()
        except etree.XMLSyntaxError as e:
            error_msg = f"Invalid XML: {str(e)}"
            self.logger.error(error_msg)
            # Create ValidationIssue for XML syntax error
            xml_error = ValidationIssue(error_msg, severity='error', node=None)
            self.all_issues.append(xml_error)
            self.total_errors += 1
            self._cleanup_if_needed()
            return

        # Pre-load all SVG XMLs
        svg_docs = self._load_svg_docs(fzp_doc)
        svg_paths = self._get_svg_paths(fzp_doc)

        self.logger.info(f"Scanning file: {self.path}")

        for check_type in check_types:
            checker = self._get_checker(check_type, fzp_doc, svg_docs)
            self.logger.debug(f"Running check: {checker.get_name()}")

            errors, warnings = checker.check()
            self.total_errors += errors
            self.total_warnings += warnings
            self.checks_run += 1
            
            # Collect issues from this checker
            self.all_issues.extend(checker.issues)

            # Apply fixes if requested and available
            if fix and (errors > 0 or warnings > 0) and hasattr(checker, 'fix'):
                if checker.fix(self.path):
                    fixes_count = checker.get_fixes_count()
                    self.errors_fixed += fixes_count
                    # Collect fixes from this checker
                    self.all_fixes.extend(checker.fixes)

        if svg_check_types:
            self._run_svg_checkers(fzp_doc, svg_docs, svg_paths, svg_check_types, fix)

        if self.total_errors > 0 or self.total_warnings > 0:
            self.logger.info(f"Total errors in {self.path}: {self.total_errors}")
            if self.total_warnings > 0:
                self.logger.info(f"Total warnings in {self.path}: {self.total_warnings}")

        fzp_doc.getroot().clear()
        for svg_doc in svg_docs.values():
            if svg_doc is not None:
                svg_doc.getroot().clear()
        self._cleanup_if_needed()

    def _parse_fzp(self):
        fzp_doc = etree.parse(self.path)
        return fzp_doc

    def _get_checker(self, check_type, fzp_doc, svg_docs):
        for checker in AVAILABLE_CHECKERS:
            if checker.get_name() == check_type:
                if checker in [
                    FZPConnectorTerminalChecker,
                    FZPConnectorSvgRefChecker,
                    FZPPCBConnectorStrokeChecker,
                    FZPLayerIDsChecker,
                    FZPMissingConnectorRefsChecker,
                    FZPMissingLegIDsChecker
                ]:
                    return checker(fzp_doc, svg_docs)
                else:
                    return checker(fzp_doc)
        raise ValueError(f"Invalid check type: {check_type}")

    def _load_svg_docs(self, fzp_doc):
        """Pre-load all SVG documents for the four views."""
        svg_docs = {}
        views_elements = fzp_doc.xpath("//views")
        if not views_elements:
            return svg_docs
        views = views_elements[0]
        for view in views.xpath("*"):
            if view.tag == "defaultUnits":
                continue
            layers_elements = view.xpath("layers")
            if layers_elements:
                layers = layers_elements[0]
                image = layers.get("image")
                if image:
                    svg_path = FZPUtils.get_svg_path(self.path, image, view.tag)
                    if svg_path and os.path.isfile(svg_path):
                        try:
                            svg_docs[view.tag] = etree.parse(svg_path)
                        except etree.XMLSyntaxError as e:
                            error_msg = f"Invalid XML in SVG {svg_path}: {str(e)}"
                            self.logger.error(error_msg)
                            # Create ValidationIssue for SVG XML syntax error
                            xml_error = ValidationIssue(error_msg, severity='error', node=None)
                            self.all_issues.append(xml_error)
                            self.total_errors += 1
                            svg_docs[view.tag] = None
                    else:
                        if svg_path:
                            error_msg = f"Missing SVG file referenced by FZP: {image}"
                            xml_error = ValidationIssue(error_msg, severity='error', node=None)
                            self.all_issues.append(xml_error)
                            self.total_errors += 1
                        svg_docs[view.tag] = None
        return svg_docs

    def _get_svg_paths(self, fzp_doc):
        """Get SVG file paths for fix operations."""
        svg_paths = {}
        views_elements = fzp_doc.xpath("//views")
        if not views_elements:
            return svg_paths
        views = views_elements[0]
        for view in views.xpath("*"):
            if view.tag == "defaultUnits":
                continue
            layers_elements = view.xpath("layers")
            if layers_elements:
                layers = layers_elements[0]
                image = layers.get("image")
                if image:
                    svg_path = FZPUtils.get_svg_path(self.path, image, view.tag)
                    if svg_path and os.path.isfile(svg_path):
                        svg_paths[view.tag] = svg_path
        return svg_paths

    def _run_svg_checkers(self, fzp_doc, svg_docs, svg_paths, svg_check_types, fix):
        views_elements = fzp_doc.xpath("//views")
        if not views_elements:
            return
        views = views_elements[0]
        for view in views.xpath("*"):
            if view.tag == "defaultUnits":
                continue
            
            svg_doc = svg_docs.get(view.tag)
            if not svg_doc:
                continue
                
            # Show which SVG file is being checked for this view
            svg_path = svg_paths.get(view.tag)
            if svg_path:
                self.logger.info(f"Checking SVG file: {svg_path}")
                # Initialize results for this SVG file if not exists
                if svg_path not in self.svg_file_results:
                    self.svg_file_results[svg_path] = {'issues': [], 'fixes': []}
                
            layers_elements = view.xpath("layers")
            if layers_elements:
                layers = layers_elements[0]
                layer_ids = []
                layer_elements = layers.xpath("layer")
                for layer_element in layer_elements:
                    layer_id = layer_element.get("layerId")
                    if layer_id:
                        layer_ids.append(layer_id)

                for check_type in svg_check_types:
                    checker = self._get_svg_checker(check_type, svg_doc, layer_ids)
                    self.logger.debug(f"Running SVG check: {checker.get_name()} for {view.tag}")
                    errors, warnings = checker.check()
                    self.total_errors += errors
                    self.total_warnings += warnings
                    self.checks_run += 1
                    
                    # Collect issues from this SVG checker for the specific SVG file
                    if svg_path and svg_path in self.svg_file_results:
                        self.svg_file_results[svg_path]['issues'].extend(checker.issues)

                    if fix and errors > 0 and hasattr(checker, 'fix'):
                        if svg_path and checker.fix(svg_path):
                            fixes_count = checker.get_fixes_count()
                            self.errors_fixed += fixes_count
                            # Collect fixes from this SVG checker for the specific SVG file
                            if svg_path in self.svg_file_results:
                                self.svg_file_results[svg_path]['fixes'].extend(checker.fixes)

    def _get_svg_checker(self, check_type, svg_doc, layer_ids):
        for checker in SVG_AVAILABLE_CHECKERS:
            if checker.get_name() == check_type:
                return checker(svg_doc, layer_ids)
        raise ValueError(f"Invalid SVG check type: {check_type}")

    def _cleanup_if_needed(self):
        """Clean up extracted fzpz contents if needed."""
        if self.extracted_dir:
            FZPUtils.cleanup_extraction(self.extracted_dir)
            self.extracted_dir = None

    def check_svg_file(self, svg_path, selected_svg_checks, fix=False):
        """Check a single SVG file directly with SVG-specific checks."""
        from lxml import etree
        
        if not os.path.isfile(svg_path):
            print(f"Error: SVG file '{svg_path}' does not exist")
            return 1
        
        try:
            svg_doc = etree.parse(svg_path)
        except etree.XMLSyntaxError as e:
            print(f"Error: Invalid XML in SVG file '{svg_path}': {str(e)}")
            return 1
        
        all_issues = []
        all_fixes = []
        
        self.logger.info(f"Checking SVG file: {svg_path}")
        
        for check_type in selected_svg_checks:
            checker = self._get_svg_checker(check_type, svg_doc, [])
            self.logger.debug(f"Running SVG check: {checker.get_name()}")
            
            errors, warnings = checker.check()
            
            # Collect issues from this checker
            all_issues.extend(checker.issues)
            
            # Apply fixes if requested
            if fix and errors > 0 and hasattr(checker, 'fix'):
                if checker.fix(svg_path):
                    # Collect fixes from this checker
                    all_fixes.extend(checker.fixes)
        
        # Create file result structure for SVG-only check
        # Treat the SVG file as the main file (like an FZP file would be)
        file_result = {
            'file': svg_path,
            'checks': len(selected_svg_checks),
            'issues': all_issues[:],  # SVG issues as main issues
            'fix_results': all_fixes[:]  # SVG fixes as main fixes
            # No 'svg_files' key since this IS the SVG file
        }
        
        # Show hint before the report
        print(f"\n💡 Hint: To find FZP files that use this SVG and run additional checks, try:")
        print(f"   python fzp_checker.py -s {svg_path} /path/to/fzp/directory")
        print(f"   Example: python fzp_checker.py -s {svg_path} contrib/")
        
        # Use the unified reporting method
        self.generate_report([file_result], verbose=self.logger.isEnabledFor(logging.DEBUG))
        
        # Return error count for exit code
        return len([issue for issue in all_issues if issue.severity == 'error'])

    def generate_github_summary(self, file_results):
        """Generate a markdown report for GitHub Actions summary"""
        # Calculate totals
        total_files_checked = len(file_results)
        total_checks_run = sum(result['checks'] for result in file_results)
        total_errors = 0
        total_warnings = 0
        total_errors_fixed = 0

        for result in file_results:
            fzp_errors = len([issue for issue in result['issues'] if issue.severity == 'error'])
            fzp_warnings = len([issue for issue in result['issues'] if issue.severity == 'warning'])
            fzp_fixes = len(result['fix_results'])

            total_errors += fzp_errors
            total_warnings += fzp_warnings
            total_errors_fixed += fzp_fixes

            if 'svg_files' in result:
                for svg_path, svg_result in result['svg_files'].items():
                    svg_errors = len([issue for issue in svg_result['issues'] if issue.severity == 'error'])
                    svg_warnings = len([issue for issue in svg_result['issues'] if issue.severity == 'warning'])
                    svg_fixes = len(svg_result['fix_results'])

                    total_errors += svg_errors
                    total_warnings += svg_warnings
                    total_errors_fixed += svg_fixes

        # Generate markdown
        md = []
        md.append("# FZP Checker Results\n")

        # Summary table
        if total_errors == 0 and total_warnings == 0:
            md.append("## ✅ All checks passed!\n")
        elif total_errors > 0:
            md.append("## ❌ Issues found\n")
        else:
            md.append("## ⚠️ Warnings found\n")

        md.append("| Metric | Count |")
        md.append("|--------|-------|")
        md.append(f"| Files checked | {total_files_checked} |")
        md.append(f"| Checks run | {total_checks_run} |")
        md.append(f"| Errors | {total_errors} |")
        md.append(f"| Warnings | {total_warnings} |")
        md.append(f"| Fixed | {total_errors_fixed} |")
        md.append("")

        # File details
        if file_results:
            md.append("## File Details\n")
            for result in file_results:
                fzp_errors = len([issue for issue in result['issues'] if issue.severity == 'error'])
                fzp_warnings = len([issue for issue in result['issues'] if issue.severity == 'warning'])
                fzp_fixes = len(result['fix_results'])

                if fzp_errors == 0 and fzp_warnings == 0:
                    status = "✅"
                elif fzp_errors > 0:
                    status = "❌"
                else:
                    status = "⚠️"

                md.append(f"### {status} `{result['file']}`")

                if fzp_errors > 0 or fzp_warnings > 0:
                    if result['issues']:
                        for issue in result['issues']:
                            icon = "🔴" if issue.severity == 'error' else "🟡"
                            md.append(f"- {icon} {issue.message}")

                if fzp_fixes > 0:
                    md.append(f"\n**Fixed:** {fzp_fixes} issue(s)")

                # SVG files
                if result.get('svg_files'):
                    for svg_file, svg_result in sorted(result['svg_files'].items()):
                        svg_errors = len([issue for issue in svg_result['issues'] if issue.severity == 'error'])
                        svg_warnings = len([issue for issue in svg_result['issues'] if issue.severity == 'warning'])

                        if svg_errors > 0 or svg_warnings > 0:
                            md.append(f"\n**SVG:** `{svg_file}`")
                            if svg_result['issues']:
                                for issue in svg_result['issues']:
                                    icon = "🔴" if issue.severity == 'error' else "🟡"
                                    md.append(f"  - {icon} {issue.message}")

                md.append("")

        return "\n".join(md)

    def generate_report(self, file_results, verbose=False):
        """Generate a formatted report for checker results"""
        # Calculate totals from the collected data
        total_files_checked = len(file_results)
        total_checks_run = sum(result['checks'] for result in file_results)
        total_errors = 0
        total_warnings = 0
        total_errors_fixed = 0
        
        # Calculate totals and add counts to each result
        for result in file_results:
            # Count FZP errors/warnings/fixes
            fzp_errors = len([issue for issue in result['issues'] if issue.severity == 'error'])
            fzp_warnings = len([issue for issue in result['issues'] if issue.severity == 'warning'])
            fzp_fixes = len(result['fix_results'])
            
            result['errors'] = fzp_errors
            result['warnings'] = fzp_warnings
            result['fixes'] = fzp_fixes
            
            total_errors += fzp_errors
            total_warnings += fzp_warnings
            total_errors_fixed += fzp_fixes
            
            # Process SVG results for this FZP
            if 'svg_files' in result:
                for svg_path, svg_result in result['svg_files'].items():
                    svg_errors = len([issue for issue in svg_result['issues'] if issue.severity == 'error'])
                    svg_warnings = len([issue for issue in svg_result['issues'] if issue.severity == 'warning'])
                    svg_fixes = len(svg_result['fix_results'])
                    
                    svg_result['errors'] = svg_errors
                    svg_result['warnings'] = svg_warnings
                    svg_result['fixes'] = svg_fixes
                    
                    total_errors += svg_errors
                    total_warnings += svg_warnings
                    total_errors_fixed += svg_fixes
        
        # Print detailed summary
        print(f"\nSummary:")
        print(f"  Files checked: {total_files_checked}")
        print(f"  Checks run: {total_checks_run}")
        print(f"  Errors found: {total_errors}")
        if total_warnings > 0:
            print(f"  Warnings found: {total_warnings}")
        print(f"  Errors fixed: {total_errors_fixed}")
        
        print(f"\nFile Details:")
        
        # Show FZP files with their associated SVG files
        for result in file_results:
            # FZP file status
            status_parts = []
            if result['errors'] == 0 and result['warnings'] == 0:
                status = "✓ CLEAN"
            else:
                if result['errors'] > 0:
                    status_parts.append(f"{result['errors']} error{'s' if result['errors'] > 1 else ''}")
                if result['warnings'] > 0:
                    status_parts.append(f"{result['warnings']} warning{'s' if result['warnings'] > 1 else ''}")
                status = "✗ " + ", ".join(status_parts)
            
            fixes_info = ""
            if result['fixes'] > 0:
                fixes_info = f" (fixed: {result['fixes']})"
                
            print(f"  {result['file']}: {status}{fixes_info}")
            
            # Show FZP-specific issues
            if result['issues']:
                for issue in result['issues']:
                    severity_icon = "✗" if issue.severity == 'error' else "⚠"
                    print(f"    {severity_icon} {issue.message}")
                    
            if result['fix_results']:
                for fix in result['fix_results']:
                    print(f"    ✓ {fix.message}")
            
            # Show associated SVG files
            if result.get('svg_files'):
                for svg_file, svg_result in sorted(result['svg_files'].items()):
                    svg_status_parts = []
                    if svg_result['errors'] == 0 and svg_result['warnings'] == 0:
                        svg_status = "✓ CLEAN"
                    else:
                        if svg_result['errors'] > 0:
                            svg_status_parts.append(f"{svg_result['errors']} error{'s' if svg_result['errors'] > 1 else ''}")
                        if svg_result['warnings'] > 0:
                            svg_status_parts.append(f"{svg_result['warnings']} warning{'s' if svg_result['warnings'] > 1 else ''}")
                        svg_status = "✗ " + ", ".join(svg_status_parts)
                    
                    svg_fixes_info = ""
                    if svg_result['fixes'] > 0:
                        svg_fixes_info = f" (fixed: {svg_result['fixes']})"
                        
                    print(f"    └── {svg_file}: {svg_status}{svg_fixes_info}")
                    
                    # Show SVG-specific issues
                    if svg_result['issues']:
                        for issue in svg_result['issues']:
                            severity_icon = "✗" if issue.severity == 'error' else "⚠"
                            print(f"        {severity_icon} {issue.message}")
                            
                    if svg_result['fix_results']:
                        for fix in svg_result['fix_results']:
                            print(f"        ✓ {fix.message}")
        
        if total_files_checked > 1:
            print()  # Extra line break after file details when multiple files

        if verbose or total_errors > 0:
            print(f"Total errors: {total_errors}")

    def search_and_check_fzp_files(self, svg_file, fzp_dir, check_types, svg_check_types):
        errors = 0
        fzp_files = self._search_fzp_files_with_svg(svg_file, fzp_dir)
        for fzp_file in fzp_files:
            self.path = fzp_file
            self.check(check_types, svg_check_types)
            errors += self.total_errors
        return errors

    def _search_fzp_files_with_svg(self, svg_file, fzp_dir):
        fzp_files = []
        svg_filename = os.path.basename(svg_file)
        is_obsolete = 'obsolete' in svg_file.split(os.sep)
        for root, dirs, files in os.walk(fzp_dir):
            if not is_obsolete and 'obsolete' in root.split(os.sep):
                continue

            for file in files:
                if file.endswith(".fzp"):
                    fzp_path = os.path.join(root, file)
                    with open(fzp_path, 'r') as f:
                        fzp_content = f.read()
                        if svg_filename in fzp_content:
                            fzp_files.append(fzp_path)
        return fzp_files

AVAILABLE_CHECKERS = [FZPMissingTagsChecker, FZPConnectorTerminalChecker, FZPConnectorSvgRefChecker, FZPPCBConnectorStrokeChecker, FZPModuleIDSpecialCharsChecker, FZPMissingLegIDsChecker, FZPMissingConnectorRefsChecker, FZPDateFormatChecker, FZPConnectorNumberingChecker]

SVG_AVAILABLE_CHECKERS = [SVGFontSizeChecker, SVGFontTypeChecker, SVGViewBoxChecker, SVGIdsChecker, SVGMatrixChecker, SVGLayerNestingChecker, SVGNoLayerChecker, SVGGornChecker, SVGCopperLayerContentChecker]
AVAILABLE_CHECKERS_FROM_GOLANG = [
    FZPFritzingVersionChecker,
    FZPFritzingVersionRangeChecker,
    FZPModuleIDChecker,
    FZPVersionChecker,
    FZPTitleChecker,
    FZPDescriptionChecker,
    FZPAuthorChecker,
    FZPViewsChecker,
    FZPBusIDChecker,
    FZPBusNodesChecker,
    FZPConnectorLayersChecker,
    FZPFamilyPropertyChecker,
    FZPUniquePropertyNamesChecker,
    FZPPropertyFieldsChecker,
    FZPRequiredTagsChecker,
    FZPBusesChecker,
    FZPLayerIDsChecker,
]
AVAILABLE_CHECKERS += AVAILABLE_CHECKERS_FROM_GOLANG

def main():
    import argparse
    import sys

    # Simple formatting
    BOLD = '\033[1m'
    RESET = '\033[0m'

    all_checkers = AVAILABLE_CHECKERS + SVG_AVAILABLE_CHECKERS

    # TODOs
    # Cleanup arguments: Remove path, --svg, replace with:
    # --basedir : directory to use as fritzing-parts dir (contains core and svg subdirs)
    # --file : Automatically detect .json, .txt, .fzp and .svg
    # Add support for directly checking .fzpz files
    parser = argparse.ArgumentParser(description="Scan FZP files for various checks")
    parser.add_argument("path", nargs='?', help="Path to FZP/FZPZ file or directory to scan")
    parser.add_argument("-c", "--checks", nargs="*", default=["all"],
                        choices=["all"] + [checker.get_name() for checker in all_checkers],
                        help="Type(s) of check to run (default: all)")
    parser.add_argument("-s", "--svg", help="Path to an SVG file. If path provided, searches for FZP files using this SVG. If no path, checks SVG directly.")
    parser.add_argument("-f", "--file", help="Path to a file containing a list of SVG and FZP files to check")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--fix", action="store_true", help="Try to automatically fix errors when possible")

    # Check for help flag to show detailed checker info
    if "-h" in sys.argv or "--help" in sys.argv:
        parser.print_help()
        print(f"\n{BOLD}Examples:{RESET}")
        print("  python fzp_checker.py mypart.fzpz              # Check an FZPZ file")
        print("  python fzp_checker.py contrib/                 # Check all FZP files in directory")
        print("  python fzp_checker.py -s myfile.svg            # Check SVG file directly")
        print(f"\n{BOLD}Available FZP checks:{RESET}")
        for checker in AVAILABLE_CHECKERS:
            print(f"{BOLD}{checker.get_name()}{RESET}:\n{checker.get_description()}\n")
        print(f"{BOLD}Available SVG checks:{RESET}")
        for checker in SVG_AVAILABLE_CHECKERS:
            print(f"{BOLD}{checker.get_name()}{RESET}:\n{checker.get_description()}\n")
        sys.exit(os.EX_OK)

    args = parser.parse_args()

    # Configure logging based on verbose flag
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Show standard help if no path provided (unless using --svg which doesn't need path)
    if not args.path and not args.svg:
        parser.print_help()
        print(f"\n{BOLD}Examples:{RESET}")
        print("  python fzp_checker.py mypart.fzpz              # Check an FZPZ file")
        print("  python fzp_checker.py contrib/                 # Check all FZP files in directory")
        print("  python fzp_checker.py -s myfile.svg            # Check SVG file directly")
        print("  python fzp_checker.py -s myfile.svg contrib/   # Find FZP files using myfile.svg")
        sys.exit(os.EX_USAGE)

    fzp_checks = [checker.get_name() for checker in AVAILABLE_CHECKERS]
    svg_checks = [checker.get_name() for checker in SVG_AVAILABLE_CHECKERS]

    if args.checks == ["all"]:
        args.checks = fzp_checks + svg_checks

    selected_fzp_checks = [check for check in args.checks if check in fzp_checks]
    selected_svg_checks = [check for check in args.checks if check in svg_checks]

    try:
        if not selected_fzp_checks and not selected_svg_checks:
            raise ValueError("No valid check types specified.")

        file_results = []  # Store results for each FZP file (including its SVG files)

        checker_runner = FZPCheckerRunner(None)

        fzp_files = set()
        file_list = []

        if args.file:
            if args.file.endswith(".json"):
                # List of strings in json format
                with open(args.file, "r") as file:
                    file_list = json.load(file)
            else:
                # Textfile, each filename on a new line
                with open(args.file, "r") as file:
                    file_list = [line.strip() for line in file]

            for filepath in file_list:
                if filepath.endswith(".fzp") or filepath.endswith(".fzpz"):
                    fzp_files.add(os.path.join(args.path, filepath))
                elif filepath.endswith(".svg"):
                    fzp_files.update(checker_runner._search_fzp_files_with_svg(filepath, args.path))
        elif args.svg and args.path and os.path.isdir(args.path):
            # Search for FZP files that reference the SVG file
            fzp_files.update(checker_runner._search_fzp_files_with_svg(args.svg, args.path))
        elif args.svg and not args.path:
            # For SVG files without path, run SVG checks directly
            exit_code = checker_runner.check_svg_file(args.svg, selected_svg_checks, fix=args.fix)
            sys.exit(os.EX_DATAERR if exit_code > 0 else os.EX_OK)
        elif os.path.isfile(args.path):
            if args.path.endswith(".fzp") or args.path.endswith(".fzpz"):
                fzp_files.add(args.path)
            else:
                print(f"Error: File {args.path} is not an FZP or FZPZ file")
                sys.exit(os.EX_DATAERR)
        elif os.path.isdir(args.path):
            for filename in sorted(os.listdir(args.path)):
                if filename.endswith(".fzp") or filename.endswith(".fzpz"):
                    fzp_files.add(os.path.join(args.path, filename))
        else:
            print(f"Error: Path '{args.path}' does not exist or is not accessible")
            sys.exit(os.EX_NOINPUT)

        # Create a logger for main function messages
        logger = logging.getLogger('fzp_checker_main')
        logger.info(f"Checking {len(fzp_files)} FZP files")

        total_errors = 0
        for fzp_file in sorted(fzp_files):
            checker_runner.path = fzp_file
            checker_runner.check(selected_fzp_checks, selected_svg_checks, fix=args.fix)
            
            # Process SVG results for this FZP - just store raw data
            svg_results_for_fzp = {}
            for svg_path, svg_result in checker_runner.svg_file_results.items():
                svg_results_for_fzp[svg_path] = {
                    'issues': svg_result['issues'][:],
                    'fix_results': svg_result['fixes'][:]
                }
            
            # Store results for this FZP file (including its SVG results) - just raw data
            file_result = {
                'file': fzp_file,
                'checks': checker_runner.checks_run,
                'issues': checker_runner.all_issues[:],  # FZP issues only
                'fix_results': checker_runner.all_fixes[:],  # FZP fixes only
                'svg_files': svg_results_for_fzp  # SVG results associated with this FZP
            }
            file_results.append(file_result)
            
            total_errors += checker_runner.total_errors

        # Generate report using the extracted method
        checker_runner.generate_report(file_results, verbose=args.verbose)

        # Write to GitHub Actions summary if running in CI
        github_summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if github_summary_file:
            try:
                markdown_report = checker_runner.generate_github_summary(file_results)
                with open(github_summary_file, 'a') as f:
                    f.write(markdown_report)
                logger.info("Report written to GitHub Actions summary")
            except Exception as e:
                logger.warning(f"Failed to write GitHub Actions summary: {e}")

        if total_errors > 0:
            sys.exit(os.EX_DATAERR)
        elif args.verbose:
            sys.exit(os.EX_OK)

    except ValueError as e:
        print(str(e))
        parser.print_help()
        sys.exit(os.EX_USAGE)

if __name__ == "__main__":
    main()
