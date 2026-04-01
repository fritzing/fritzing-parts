from .fzp_checkers import FZPChecker
from .fzp_utils import FZPUtils
from lxml import etree
import os

class FZPMissingConnectorRefsChecker(FZPChecker):
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

    def check(self):
        view_layers = {
            'pcbView': ['copper0', 'copper1'],
            'breadboardView': ['breadboard'],
            'schematicView': ['schematic']
        }

        for view_name, layers in view_layers.items():
            svg_doc = self.svg_docs.get(view_name)
            if not svg_doc:
                continue

            try:
                connector_layers = {}
                connector_nodes = {}  # Store the actual nodes

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
                                connector_nodes[connector_id] = connector  # Store the node
                            connector_layers[connector_id].add(layer)

                # Check FZP references for each connector's required layers
                for connector_id, required_layers in connector_layers.items():
                    connector_num = connector_id.replace('connector', '').replace('pin', '').replace('pad', '')
                    connector_node = connector_nodes[connector_id]
                    for layer in required_layers:
                        refs = self.fzp_doc.xpath(f"//connector[@id='connector{connector_num}']/views/{view_name}/p[@layer='{layer}']")
                        if not refs:
                            self.add_error(f"Connector {connector_id} is in {layer} layer in SVG but not referenced in FZP {view_name}", node=connector_node)

            except Exception as e:
                self.add_error(f"Error processing {view_name} SVG: {str(e)}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "missing_connector_refs"

    @staticmethod
    def get_description():
        return "Check that all connectors in SVG layer groups are properly referenced in FZP"
