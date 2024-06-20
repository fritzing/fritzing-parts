import os
from lxml import etree
from abc import ABC, abstractmethod
from fzp_utils import FZPUtils
from svg_utils import SVGUtils

class FZPChecker(ABC):
    def __init__(self, fzp_doc):
        self.fzp_doc = fzp_doc

    @abstractmethod
    def check(self):
        pass

    @staticmethod
    @abstractmethod
    def get_name():
        pass

    @staticmethod
    @abstractmethod
    def get_description():
        pass


class FZPMissingTagsChecker(FZPChecker):
    def check(self):
        errors = 0
        required_tags = ["module", "version", "author", "title", "label", "date", "description", "views", "connectors"]
        for tag in required_tags:
            if not self.fzp_doc.xpath(f"//{tag}"):
                print(f"Missing required tag: {tag}")
                errors += 1
        return errors

    @staticmethod
    def get_name():
        return "missing_tags"

    @staticmethod
    def get_description():
        return "Check for missing required tags in the FZP file"


class FZPConnectorTerminalChecker(FZPChecker):
    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path

    def check(self):
        errors = 0
        connectors_section = self.fzp_doc.xpath("//module/connectors")
        if connectors_section:
            connectors = connectors_section[0].xpath("connector")
            for connector in connectors:
                connector_id = connector.attrib["id"]
                views = connector.xpath("views")[0]
                for view in views:
                    terminal_ids = []
                    if view.tag != "schematicView":
                        continue

                    terminal_ids.extend([p.attrib["terminalId"] for p in view.xpath("p[@terminalId]")])
                    for terminal_id in terminal_ids:
                        if not self.svg_has_element_with_id(terminal_id, view.tag):
                            print(f"Connector {connector_id} references missing terminal {terminal_id} in SVG")
                            errors += 1
        return errors

    def svg_has_element_with_id(self, element_id, view_name):
        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, view_name)
        if not svg_path:
            return True  # Skip template SVGs
        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{element_id}']")
            return len(elements) > 0
        except FileNotFoundError:
            print(f"SVG file not found: {svg_path}")
            return True  # Not a 'missing element' if the complete file is missing
        except etree.XMLSyntaxError as err:
            print(f"Error parsing SVG file: {svg_path}")
            print(str(err))
        return False

    @staticmethod
    def get_name():
        return "connector_terminal"

    @staticmethod
    def get_description():
        return "Check if the connector terminals defined in the FZP file exist in the referenced SVGs"


class FZPConnectorVisibilityChecker(FZPChecker):
    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path

    def check(self):
        errors = 0
        connectors_section = self.fzp_doc.xpath("//module/connectors")
        if connectors_section:
            connectors = connectors_section[0].xpath("connector")
            for connector in connectors:
                connector_id = connector.attrib["id"]

                views = connector.xpath("views")[0]
                for view in views:
                    p_elements = view.xpath("p")
                    for p in p_elements:
                        if FZPUtils.is_hybrid_or_unknown_layer(p):
                            continue

                        connector_svg_id = p.attrib.get("svgId")
                        layer = p.attrib.get("layer")
                        if not connector_svg_id:
                            print(f"Connector {connector_id} does not reference an element in layer {layer}.")
                            errors += 1
                            continue

                        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, view.tag, layer)
                        if not svg_path:
                            continue  # Skip template SVGs
                        if not self.is_connector_visible(svg_path, connector_svg_id): # we already checked that it is not hybrid
                            print(f"Invisible connector '{connector_svg_id}' in layer '{layer}' of file '{self.fzp_path}'")
                            errors += 1
        return errors

    def is_connector_visible(self, svg_path, connector_id):
        if not os.path.isfile(svg_path):
            print(f"Warning: Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True  # Skip the check if the SVG path is invalid

        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{connector_id}']")
            if elements:
                try:
                    return SVGUtils.has_visible_attributes_recursive(elements[0])
                except ValueError as e:
                    print(f"Error in {connector_id} : {e}")
                    return False
        except FileNotFoundError:
            print(f"SVG file not found: {svg_path}")
        except etree.XMLSyntaxError as err:
            print(f"Error parsing SVG file: {svg_path}")
            print(str(err))
        return False

    @staticmethod
    def get_name():
        return "connector_visibility"

    @staticmethod
    def get_description():
        return "Check for invisible (non-hybrid) connectors in the SVG files referenced by the FZP"


class FZPPCBConnectorStrokeChecker(FZPChecker):
    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path
        self.errors = 0

    def check(self):
        connectors_section = self.fzp_doc.xpath("//module/connectors")
        if connectors_section:
            connectors = connectors_section[0].xpath("connector")
            for connector in connectors:
                connector_id = connector.attrib["id"]

                views = connector.xpath("views")[0]
                for view in views:
                    if view.tag != "pcbView":
                        continue

                    p_elements = view.xpath("p")
                    for p in p_elements:
                        connector_svg_id = p.attrib.get("svgId")
                        if not connector_svg_id:
                            continue

                        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, view.tag)
                        if not svg_path:
                            continue  # Skip template SVGs
                        if not self.is_connector_stroke_valid(svg_path, connector_svg_id):
                            print(f"Invalid stroke for connector '{connector_svg_id}' in PCB view of file '{self.fzp_path}'")
                            self.errors += 1
        return self.errors

    def is_connector_stroke_valid(self, svg_path, connector_id):
        if not os.path.isfile(svg_path):
            print(f"Warning: Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True  # Skip the check if the SVG path is invalid

        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{connector_id}']")
            if elements:
                try:
                    return SVGUtils.has_valid_stroke(elements[0])
                except ValueError as e:
                    self.errors += 1
                    print(f"Error in {connector_id}: {e}")
                    return True # Connector not found, skip further checks
            else:
                self.errors += 1
                print(f"Warning: Connector {connector_id} not found in {svg_path}")
                return True
        except FileNotFoundError:
            self.errors += 1
            print(f"SVG file not found: {svg_path}")
            return True
        except etree.XMLSyntaxError as err:
            self.errors += 1
            print(f"Error parsing SVG file: {svg_path}")
            print(str(err))
            return True
        return False

    @staticmethod
    def get_name():
        return "pcb_connector_stroke"

    @staticmethod
    def get_description():
        return "Check for valid stroke attributes in connectors of the PCB view in the SVG files referenced by the FZP"
