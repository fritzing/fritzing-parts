import os
import xml.dom.minidom
from abc import ABC, abstractmethod
from fzp_utils import FZPUtils

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

class FZPValidXMLChecker(FZPChecker):
    def check(self):
        errors = 0
        try:
            xml.dom.minidom.parseString(self.fzp_doc.toxml())
        except xml.parsers.expat.ExpatError as e:
            print(f"Invalid XML: {str(e)}")
            errors += 1
        return errors

    @staticmethod
    def get_name():
        return "valid_xml"

    @staticmethod
    def get_description():
        return "Check if the FZP file is a valid XML document"

class FZPMissingTagsChecker(FZPChecker):
    def check(self):
        errors = 0
        required_tags = ["module", "version", "author", "title", "label", "date", "description", "views", "connectors"]
        for tag in required_tags:
            if not self.fzp_doc.getElementsByTagName(tag):
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
        connectors_section = self.fzp_doc.getElementsByTagName("module")[0].getElementsByTagName("connectors")
        if connectors_section:
            connectors = connectors_section[0].getElementsByTagName("connector")
            for connector in connectors:
                connector_id = connector.getAttribute("id")
                views = connector.getElementsByTagName("views")[0]
                for view in views.childNodes:
                    terminal_ids = []
                    if view.nodeType == view.ELEMENT_NODE:
                        if view.tagName != "schematicView":
                            continue

                        terminal_ids.extend([p.getAttribute("terminalId") for p in view.getElementsByTagName("p") if
                                             p.hasAttribute("terminalId")])
                    for terminal_id in terminal_ids:
                        if not self.svg_has_element_with_id(terminal_id, view.tagName):
                            print(f"Connector {connector_id} references missing terminal {terminal_id} in SVG")
                            errors += 1
        return errors

    def svg_has_element_with_id(self, element_id, view_name):
        views = self.fzp_doc.getElementsByTagName("views")[0]
        for view in views.childNodes:
            if view.nodeType == view.ELEMENT_NODE and view.tagName == view_name:
                layers = view.getElementsByTagName("layers")[0]
                image = layers.getAttribute("image")
                if image:
                    svg_path = FZPUtils.get_svg_path(self.fzp_path, image)
                    if FZPUtils.is_template(svg_path, view_name):
                        return True # We assume the template has the requested ID
                    try:
                        svg_doc = xml.dom.minidom.parse(svg_path)
                        elements = svg_doc.getElementsByTagName("*")
                        for element in elements:
                            if element.getAttribute("id") == element_id:
                                return True
                    except FileNotFoundError:
                        print(f"SVG file not found: {svg_path}")
                        return True # Not a 'missing element' if the complete file is missing
                    except xml.parsers.expat.ExpatError as err:
                        print(f"Error parsing SVG file: {svg_path}")
                        print(str(err))
        return False

    @staticmethod
    def get_name():
        return "connector_terminal"

    @staticmethod
    def get_description():
        return "Check if the connector terminals defined in the FZP file exist in the referenced SVGs"

