from xml.dom import minidom
from svg_checkers import SVGFontSizeChecker, SVGViewBoxChecker, SVGIdsChecker

AVAILABLE_CHECKERS = [SVGFontSizeChecker, SVGViewBoxChecker, SVGIdsChecker]


class SVGChecker:
    def __init__(self, path):
        self.path = path

    def check(self, check_types):
        svg_doc = self._parse_svg()

        for check_type in check_types:
            checker = self._get_checker(check_type, svg_doc)
            checker.check()

        # Close the SVG file
        svg_doc.unlink()

    def _parse_svg(self):
        svg_doc = minidom.parse(self.path)
        return svg_doc

    def _get_checker(self, check_type, svg_doc):
        for checker in AVAILABLE_CHECKERS:
            if check_type == "all" or checker.get_name() == check_type:
                return checker(svg_doc)
        raise ValueError(f"Invalid check type: {check_type}")


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Scan SVG files for various checks")
    parser.add_argument("path", help="Path to SVG file or directory to scan")
    parser.add_argument("checks", nargs="+", choices=[checker.get_name() for checker in AVAILABLE_CHECKERS],
                        help="Type(s) of check to run")
    args = parser.parse_args()

    if not args.checks:
        print("Available checks:")
        for checker in AVAILABLE_CHECKERS:
            print(f"{checker.get_name()}: {checker.get_description()}")
        parser.print_help()
        exit()

    try:
        if os.path.isfile(args.path):
            print(f"Scanning file: {args.path}")
            checker = SVGChecker(args.path)
            checker.check(args.checks)
        elif os.path.isdir(args.path):
            print(f"Scanning directory: {args.path}")
            for filename in os.listdir(args.path):
                if filename.endswith(".svg"):
                    filepath = os.path.join(args.path, filename)
                    print(f"Scanning file: {filepath}")
                    checker = SVGChecker(filepath)
                    checker.check(args.checks)
        else:
            print(f"Invalid path: {args.path}")
    except ValueError as e:
        print(str(e))
        parser.print_help()
