from .fzp_checkers import FZPChecker
from .fzp_utils import FZPUtils
from lxml import etree

class FZPMissingLegIDsChecker(FZPChecker):
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

    def check(self):
        breadboard_svg = self.svg_docs.get('breadboardView')
        if not breadboard_svg:
            return self.get_result()  # Skip if no breadboard SVG

        try:
            leg_elements = breadboard_svg.xpath("//*[contains(@id, 'leg')]")

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
                    self.add_error(f"Leg ID '{leg_id}' from SVG not referenced in any FZP connector", node=leg)

        except Exception as e:
            self.add_error(f"Error processing breadboard SVG: {str(e)}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "missing_leg_ids"

    @staticmethod
    def get_description():
        return "Check that leg IDs defined in SVG are properly referenced in FZP"
