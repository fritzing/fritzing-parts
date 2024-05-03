from xml.dom import minidom
from svg_checkers import SVGFontSizeChecker, SVGViewBoxChecker, SVGIdsChecker, SVGInvisibleConnectorsChecker

AVAILABLE_CHECKERS = [SVGFontSizeChecker, SVGViewBoxChecker, SVGIdsChecker, SVGInvisibleConnectorsChecker]

class SVGCheckerRunner:
    def __init__(self, path, verbose=False):
        self.path = path
        self.verbose = verbose
        self.total_errors = 0

    def check(self, check_types):
        svg_doc = self._parse_svg()
        if self.verbose:
            print(f"Scanning file: {self.path}")

        for check_type in check_types:
            checker = self._get_checker(check_type, svg_doc)
            errors = checker.check()
            self.total_errors += errors

        if self.verbose or self.total_errors > 0:
            print(f"Total errors in {self.path}: {self.total_errors}")
        svg_doc.unlink()

    def _parse_svg(self):
        svg_doc = minidom.parse(self.path)
        return svg_doc

    def _get_checker(self, check_type, svg_doc):
        for checker in AVAILABLE_CHECKERS:
            if check_type == "all" or checker.get_name() == check_type:
                return checker(svg_doc)
        raise ValueError(f"Invalid check type: {check_type}")


AVAILABLE_CHECKERS = [SVGFontSizeChecker, SVGViewBoxChecker, SVGIdsChecker, SVGInvisibleConnectorsChecker]


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Scan SVG files for various checks")
    parser.add_argument("path", help="Path to SVG file or directory to scan")
    parser.add_argument("checks", nargs="+", choices=[checker.get_name() for checker in AVAILABLE_CHECKERS],
                        help="Type(s) of check to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    if not args.checks:
        print("Available checks:")
        for checker in AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}: {checker.get_description()}")
        parser.print_help()
        exit()

    try:
        if os.path.isfile(args.path):
            checker_runner = SVGCheckerRunner(args.path, verbose=args.verbose)
            checker_runner.check(args.checks)
        elif os.path.isdir(args.path):
            if args.verbose:
                print(f"Scanning directory: {args.path}")
            total_errors = 0
            for filename in os.listdir(args.path):
                if filename.endswith(".svg"):
                    filepath = os.path.join(args.path, filename)
                    checker_runner = SVGCheckerRunner(filepath, verbose=args.verbose)
                    checker_runner.check(args.checks)
                    total_errors += checker_runner.total_errors
            if args.verbose or total_errors > 0:
                print(f"Total errors in directory: {total_errors}")
        else:
            print(f"Invalid path: {args.path}")
    except ValueError as e:
        print(str(e))
        parser.print_help()