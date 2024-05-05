from xml.dom import minidom
import re
from fzp_checkers import *
from svg_checker_runner import SVGCheckerRunner, AVAILABLE_CHECKERS as SVG_AVAILABLE_CHECKERS
from fzp_utils import FZPUtils


class FZPCheckerRunner:
    def __init__(self, path, verbose=False):
        self.path = path
        self.verbose = verbose
        self.total_errors = 0

    def check(self, check_types, svg_check_types):
        fzp_doc = self._parse_fzp()
        if self.verbose:
            print(f"Scanning file: {self.path}")

        for check_type in check_types:
            checker = self._get_checker(check_type, fzp_doc)
            errors = checker.check()
            self.total_errors += errors

        if svg_check_types:
            self._run_svg_checkers(fzp_doc, svg_check_types)

        if self.verbose or self.total_errors > 0:
            print(f"Total errors in {self.path}: {self.total_errors}")
        fzp_doc.unlink()

    def _parse_fzp(self):
        fzp_doc = xml.dom.minidom.parse(self.path)
        return fzp_doc

    def _get_checker(self, check_type, fzp_doc):
        for checker in AVAILABLE_CHECKERS:
            if checker.get_name() == check_type:
                if checker == FZPConnectorTerminalChecker:
                    return checker(fzp_doc, self.path)
                else:
                    return checker(fzp_doc)
        raise ValueError(f"Invalid check type: {check_type}")

    def _run_svg_checkers(self, fzp_doc, svg_check_types):
        views = fzp_doc.getElementsByTagName("views")[0]
        for view in views.childNodes:
            if view.nodeType == view.ELEMENT_NODE:
                layers_elements = view.getElementsByTagName("layers")
                if layers_elements:
                    layers = layers_elements[0]
                    image = layers.getAttribute("image")
                    if image:
                        svg_path = self._get_svg(image)
                        if os.path.isfile(svg_path):
                            svg_checker_runner = SVGCheckerRunner(svg_path, verbose=self.verbose)
                            svg_checker_runner.check(svg_check_types)
                            self.total_errors += svg_checker_runner.total_errors
                        else:
                            if FZPUtils.is_template(svg_path, view.tagName):
                                continue
                            else:
                                print(f"Warning: SVG '{svg_path}' for view '{view.tagName}' of file '{self.path}' not found.")
                                self.total_errors += 1
                else:
                    print(f"Warning: No 'layers' element found in view '{view.tagName}' of file '{self.path}'")

AVAILABLE_CHECKERS = [FZPValidXMLChecker, FZPMissingTagsChecker, FZPConnectorTerminalChecker]

if __name__ == "__main__":
    import argparse

    all_checkers = AVAILABLE_CHECKERS + SVG_AVAILABLE_CHECKERS

    parser = argparse.ArgumentParser(description="Scan FZP files for various checks")
    parser.add_argument("path", help="Path to FZP file or directory to scan")
    parser.add_argument("checks", nargs="*",
                        choices=[checker.get_name() for checker in all_checkers],
                        help="Type(s) of check to run (default: all)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    fzp_checks = [checker.get_name() for checker in AVAILABLE_CHECKERS]
    svg_checks = [checker.get_name() for checker in SVG_AVAILABLE_CHECKERS]

    if not args.checks:
        args.checks = fzp_checks

    selected_fzp_checks = [check for check in args.checks if check in fzp_checks]
    selected_svg_checks = [check for check in args.checks if check in svg_checks]

    if not selected_fzp_checks and not selected_svg_checks:
        print("Available FZP checks:")
        for checker in AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}: {checker.get_description()}")
        print("\nAvailable SVG checks:")
        for checker in SVG_AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}: {checker.get_description()}")
        parser.print_help()
        exit()

    try:
        if os.path.isfile(args.path):
            checker_runner = FZPCheckerRunner(args.path, verbose=args.verbose)
            checker_runner.check(selected_fzp_checks, selected_svg_checks)
        elif os.path.isdir(args.path):
            if args.verbose:
                print(f"Scanning directory: {args.path}")
            total_errors = 0
            for filename in os.listdir(args.path):
                if filename.endswith(".fzp"):
                    filepath = os.path.join(args.path, filename)
                    checker_runner = FZPCheckerRunner(filepath, verbose=args.verbose)
                    checker_runner.check(selected_fzp_checks, selected_svg_checks)
                    total_errors += checker_runner.total_errors
            if args.verbose or total_errors > 0:
                print(f"Total errors in directory: {total_errors}")
        else:
            print(f"Invalid path: {args.path}")
    except ValueError as e:
        print(str(e))
        parser.print_help()