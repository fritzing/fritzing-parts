from xml.dom import minidom
from fzp_checkers import *
from svg_checker_runner import SVGCheckerRunner, AVAILABLE_CHECKERS as SVG_AVAILABLE_CHECKERS

class FZPCheckerRunner:
    def __init__(self, path, verbose=False):
        self.path = path
        self.verbose = verbose
        self.total_errors = 0

    def check(self, check_types):
        fzp_doc = self._parse_fzp()
        if self.verbose:
            print(f"Scanning file: {self.path}")

        for check_type in check_types:
            if check_type == "svg":
                self._run_svg_checkers(fzp_doc)
            else:
                checker = self._get_checker(check_type, fzp_doc)
                errors = checker.check()
                self.total_errors += errors

        if self.verbose or self.total_errors > 0:
            print(f"Total errors in {self.path}: {self.total_errors}")
        fzp_doc.unlink()

    def _parse_fzp(self):
        fzp_doc = xml.dom.minidom.parse(self.path)
        return fzp_doc

    def _get_checker(self, check_type, fzp_doc):
        for checker in AVAILABLE_CHECKERS:
            if check_type == "all" or checker.get_name() == check_type:
                return checker(fzp_doc)
        raise ValueError(f"Invalid check type: {check_type}")

    def _run_svg_checkers(self, fzp_doc):
        views = fzp_doc.getElementsByTagName("views")[0]
        for view in views.childNodes:
            if view.nodeType == view.ELEMENT_NODE:
                layers_elements = view.getElementsByTagName("layers")
                if layers_elements:
                    layers = layers_elements[0]
                    image = layers.getAttribute("image")
                    if image:
                        svg_path = os.path.join(os.path.dirname(self.path), image)
                        if os.path.isfile(svg_path):
                            svg_checker_runner = SVGCheckerRunner(svg_path, verbose=self.verbose)
                            svg_checker_runner.check(["all"])
                            self.total_errors += svg_checker_runner.total_errors
                else:
                    print(f"Warning: No 'layers' element found in view '{view.tagName}' of file '{self.path}'")

AVAILABLE_CHECKERS = [FZPValidXMLChecker, FZPMissingTagsChecker, FZPConnectorTerminalChecker]

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scan FZP files for various checks")
    parser.add_argument("path", help="Path to FZP file or directory to scan")
    parser.add_argument("checks", nargs="+",
                        choices=[checker.get_name() for checker in AVAILABLE_CHECKERS] + ["svg"],
                        help="Type(s) of check to run (including 'svg' for SVG checks)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if not args.checks:
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
            checker_runner.check(args.checks)
        elif os.path.isdir(args.path):
            if args.verbose:
                print(f"Scanning directory: {args.path}")
            total_errors = 0
            for filename in os.listdir(args.path):
                if filename.endswith(".fzp"):
                    filepath = os.path.join(args.path, filename)
                    checker_runner = FZPCheckerRunner(filepath, verbose=args.verbose)
                    checker_runner.check(args.checks)
                    total_errors += checker_runner.total_errors
            if args.verbose or total_errors > 0:
                print(f"Total errors in directory: {total_errors}")
        else:
            print(f"Invalid path: {args.path}")
    except ValueError as e:
        print(str(e))
        parser.print_help()