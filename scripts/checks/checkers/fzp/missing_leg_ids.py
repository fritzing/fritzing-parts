from fzp_checkers import FZPChecker
from fzp_utils import FZPUtils
from lxml import etree

class FZPMissingLegIDsChecker(FZPChecker):
    needs_path = True

    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path

    def check(self):
        print(f"Checking FZP path: {self.fzp_path}")
        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, "breadboardView")
        print(f"Found SVG path: {svg_path}")

        if not svg_path:
            return self.get_result()  # Skip template SVGs

        try:
            svg_doc = etree.parse(svg_path)
            leg_elements = svg_doc.xpath("//*[contains(@id, 'leg')]")

            # First collect all leg IDs referenced in the FZP
            referenced_legs = set()
            for breadboard_view in self.fzp_doc.xpath("//breadboardView"):
                for p_elem in breadboard_view.xpath("p[@legId]"):
                    referenced_legs.add(p_elem.get('legId'))

            # Check that all legs in SVG are referenced somewhere in the FZP
            for leg in leg_elements:
                leg_id = leg.get("id")
                if not leg_id or not leg_id.startswith("connector") or not leg_id.endswith("leg"):
                    continue

                if leg_id not in referenced_legs:
                    self.add_error(f"Leg ID '{leg_id}' from SVG not referenced in any FZP connector")

        except (FileNotFoundError, OSError, etree.XMLSyntaxError) as e:
            self.add_error(f"Error processing SVG file {svg_path}: {str(e)}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "missing_leg_ids"

    @staticmethod
    def get_description():
        return "Check that leg IDs defined in SVG are properly referenced in FZP"
