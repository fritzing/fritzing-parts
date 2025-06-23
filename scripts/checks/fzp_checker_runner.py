from lxml import etree
from fzp_checkers import *
from svg_checkers import *
from checkers import *
from checkers import additional_fzp_checkers  # Gets the class list for AVAILABLE_CHECKERS
from fzp_utils import FZPUtils
import json
import re
import os

class FZPCheckerRunner:
    def __init__(self, path, verbose=False):
        self.path = path
        self.verbose = verbose
        self.total_errors = 0
        self.total_warnings = 0
        self.fixed = False
        self.extracted_dir = None  # For fzpz cleanup

    def check(self, check_types, svg_check_types, fix=False):
        self.total_errors = 0
        self.total_warnings = 0
        self.fixed = False
        
        # Handle fzpz files
        original_path = self.path
        if self.path.endswith('.fzpz'):
            try:
                self.path = FZPUtils.extract_fzpz(self.path)
                self.extracted_dir = os.path.dirname(self.path)
                if self.verbose:
                    print(f"Extracted FZPZ to: {self.extracted_dir}")
            except Exception as e:
                print(f"Error extracting FZPZ file {original_path}: {str(e)}")
                self.total_errors += 1
                return
        
        try:
            fzp_doc = self._parse_fzp()
        except etree.XMLSyntaxError as e:
            print(f"Invalid XML: {str(e)}")
            self.total_errors += 1
            self._cleanup_if_needed()
            return

        if self.verbose:
            print(f"Scanning file: {self.path}")

        for check_type in check_types:
            checker = self._get_checker(check_type, fzp_doc)
            if self.verbose:
                print(f"Running check: {checker.get_name()}")

            errors, warnings = checker.check()
            self.total_errors += errors
            self.total_warnings += warnings

            # Apply fixes if requested and available
            if fix and errors > 0 and hasattr(checker, 'fix'):
                try:
                    if checker.fix():
                        self.fixed = True
                except Exception as e:
                    print(f"Error while fixing: {str(e)}")
                    continue

        if svg_check_types:
            self._run_svg_checkers(fzp_doc, svg_check_types, fix)

        if self.verbose or self.total_errors > 0 or self.total_warnings > 0:
            print(f"Total errors in {self.path}: {self.total_errors}")
            if self.total_warnings > 0:
                print(f"Total warnings in {self.path}: {self.total_warnings}")

        fzp_doc.getroot().clear()
        self._cleanup_if_needed()

    def _parse_fzp(self):
        fzp_doc = etree.parse(self.path)
        return fzp_doc

    def _get_checker(self, check_type, fzp_doc):
        for checker in AVAILABLE_CHECKERS:
            if checker.get_name() == check_type:
                if checker in [
                    FZPConnectorTerminalChecker,
                    FZPConnectorVisibilityChecker,
                    FZPPCBConnectorStrokeChecker,
                    FZPBusNodesChecker,
                    FZPLayerIDsChecker,
                ] or checker.needs_path:
                    return checker(fzp_doc, self.path)
                else:
                    return checker(fzp_doc)
        raise ValueError(f"Invalid check type: {check_type}")

    def _run_svg_checkers(self, fzp_doc, svg_check_types, fix):
        views = fzp_doc.xpath("//views")[0]
        for view in views.xpath("*"):
            if view.tag == "defaultUnits":
                # defaultUnits seems unused in Fritzing.
                # Write a script to remove this from all core parts?
                continue
            layers_elements = view.xpath("layers")
            if layers_elements:
                layers = layers_elements[0]
                image = layers.get("image")

                layer_ids = []
                layer_elements = layers.xpath("layer")
                for layer_element in layer_elements:
                    layer_id = layer_element.get("layerId")
                    if layer_id:
                        layer_ids.append(layer_id)

                if image:
                    svg_path = FZPUtils.get_svg_path(self.path, image,
                                                     view.tag)  # Pass view.tag as the additional parameter
                    if svg_path is None:
                        continue  # Skip template SVGs
                    if os.path.isfile(svg_path):
                        try:
                            svg_doc = etree.parse(svg_path)
                            for check_type in svg_check_types:
                                checker = self._get_svg_checker(check_type, svg_doc, layer_ids)
                                if self.verbose:
                                    print(f"Running SVG check: {checker.get_name()} on {svg_path} for {view.tag}")
                                errors, warnings = checker.check()
                                self.total_errors += errors
                                self.total_warnings += warnings

                                if fix and errors > 0 and hasattr(checker, 'fix'):
                                    try:
                                        if checker.fix():
                                            self.fixed = True
                                    except Exception as e:
                                        print(f"Error while fixing: {str(e)}")

                            svg_doc.getroot().clear()
                        except etree.XMLSyntaxError as e:
                            print(f"Invalid XML in SVG: {str(e)}")
                            self.total_errors += 1

                    else:
                        print(f"Warning: SVG '{svg_path}' for view '{view.tag}' of file '{self.path}' not found.")
                        self.total_errors += 1
            else:
                print(f"Warning: No 'layers' element found in view '{view.tag}' of file '{self.path}'")

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

AVAILABLE_CHECKERS = [FZPMissingTagsChecker, FZPConnectorTerminalChecker, FZPConnectorVisibilityChecker, FZPPCBConnectorStrokeChecker, FZPModuleIDSpecialCharsChecker]
SVG_AVAILABLE_CHECKERS = [SVGFontSizeChecker, SVGFontTypeChecker, SVGViewBoxChecker, SVGIdsChecker, SVGMatrixChecker, SVGLayerNestingChecker]
AVAILABLE_CHECKERS_FROM_GOLANG = [
    FZPFritzingVersionChecker,
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
AVAILABLE_CHECKERS.extend(additional_fzp_checkers)

if __name__ == "__main__":
    import argparse

    all_checkers = AVAILABLE_CHECKERS + SVG_AVAILABLE_CHECKERS

    # TODOs
    # Cleanup arguments: Remove path, --svg, replace with:
    # --basedir : directory to use as fritzing-parts dir (contains core and svg subdirs)
    # --file : Automatically detect .json, .txt, .fzp and .svg
    # Add support for directly checking .fzpz files
    parser = argparse.ArgumentParser(description="Scan FZP files for various checks", add_help=False)
    parser.add_argument("path", help="Path to FZP/FZPZ file or directory to scan")
    parser.add_argument("-c", "--checks", nargs="*", default=["all"],
                        choices=["all"] + [checker.get_name() for checker in all_checkers],
                        help="Type(s) of check to run (default: all)")
    parser.add_argument("-s", "--svg", help="Path to an SVG file to search for in FZP files")
    parser.add_argument("-f", "--file", help="Path to a file containing a list of SVG and FZP files to check")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')
    parser.add_argument("--fix", action="store_true", help="Try to automatically fix errors when possible")
    parser.usage = parser.format_help()

    args = parser.parse_args()

    if args.help:
        print("\nAvailable FZP checks:")
        for checker in AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}:\n{checker.get_description()}\n")
        print("Available SVG checks:")
        for checker in SVG_AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}:\n{checker.get_description()}\n")
        parser.print_help()
        exit()

    fzp_checks = [checker.get_name() for checker in AVAILABLE_CHECKERS]
    svg_checks = [checker.get_name() for checker in SVG_AVAILABLE_CHECKERS]

    if args.checks == ["all"]:
        args.checks = fzp_checks + svg_checks

    selected_fzp_checks = [check for check in args.checks if check in fzp_checks]
    selected_svg_checks = [check for check in args.checks if check in svg_checks]

    try:
        if not selected_fzp_checks and not selected_svg_checks:
            raise ValueError("No valid check types specified.")

        total_errors = 0
        total_warnings = 0

        checker_runner = FZPCheckerRunner(None, verbose=args.verbose)

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
        elif args.svg and os.path.isdir(args.path):
            fzp_files.update(checker_runner._search_fzp_files_with_svg(args.svg, args.path))
        elif os.path.isfile(args.path):
            if args.path.endswith(".fzp") or args.path.endswith(".fzpz"):
                fzp_files.add(args.path)
            else:
                print(f"Error: File {args.path} is not an FZP or FZPZ file")
                exit(-1)
        elif os.path.isdir(args.path):
            for filename in sorted(os.listdir(args.path)):
                if filename.endswith(".fzp") or filename.endswith(".fzpz"):
                    fzp_files.add(os.path.join(args.path, filename))

        if args.verbose:
            print(f"Checking {len(fzp_files)} FZP files")

        for fzp_file in sorted(fzp_files):
            checker_runner.path = fzp_file
            checker_runner.check(selected_fzp_checks, selected_svg_checks, fix=args.fix)
            total_errors += checker_runner.total_errors

        if args.verbose or total_errors > 0:
            print(f"Total errors: {total_errors}")
            exit(total_errors)

    except ValueError as e:
        print(str(e))
        parser.print_help()
        exit(-1)
