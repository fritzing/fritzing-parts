from fzp_checkers import FZPChecker
from fzp_utils import FZPUtils
from lxml import etree
import os

class FZPMissingConnectorRefsChecker(FZPChecker):
    needs_path = True

    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path

    def check(self):
        view_layers = {
            'pcbView': ['copper0', 'copper1'],
            'breadboardView': ['breadboard'],
            'schematicView': ['schematic']
        }

        for view_name, layers in view_layers.items():
            view = self.fzp_doc.xpath(f"//views/{view_name}/layers")
            if not view:
                continue

            image = view[0].get("image")
            if not image:
                continue

            svg_path = FZPUtils.get_svg_path(self.fzp_path, image, view_name)
            if not svg_path:
                continue  # Skip template SVGs

            try:
                svg_doc = etree.parse(svg_path)
                connector_layers = {}

                # Find connectors in each layer for this view
                for layer in layers:
                    layer_groups = svg_doc.xpath(f"//*[@id='{layer}']")
                    for group in layer_groups:
                        connectors = group.xpath(".//*[starts-with(@id, 'connector') and (contains(@id, 'pin') or contains(@id, 'pad'))]")
                        for connector in connectors:
                            connector_id = connector.get('id')
                            if not connector_id:
                                continue

                            if connector_id not in connector_layers:
                                connector_layers[connector_id] = set()
                            connector_layers[connector_id].add(layer)

                # Check FZP references for each connector's required layers
                for connector_id, required_layers in connector_layers.items():
                    connector_num = connector_id.replace('connector', '').replace('pin', '').replace('pad', '')
                    for layer in required_layers:
                        refs = self.fzp_doc.xpath(f"//connector[@id='connector{connector_num}']/views/{view_name}/p[@layer='{layer}']")
                        if not refs:
                            self.add_error(f"Connector {connector_id} is in {layer} layer in SVG but not referenced in FZP {view_name}")

            except (FileNotFoundError, OSError, etree.XMLSyntaxError) as e:
                self.add_error(f"Error processing SVG file {svg_path}: {str(e)}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "missing_connector_refs"

    @staticmethod
    def get_description():
        return "Check that all connectors in SVG layer groups are properly referenced in FZP"
