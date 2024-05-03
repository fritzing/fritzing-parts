import os
import xml.dom.minidom
from abc import ABC, abstractmethod

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
    def check(self):
        errors = 0
        connectors = self.fzp_doc.getElementsByTagName("connector")
        for connector in connectors:
            connector_id = connector.getAttribute("id")
            views = connector.getElementsByTagName("views")[0]
            terminal_ids = []
            for view in views.childNodes:
                if view.nodeType == view.ELEMENT_NODE:
                    terminal_ids.extend([p.getAttribute("terminalId") for p in view.getElementsByTagName("p") if p.hasAttribute("terminalId")])
            for terminal_id in terminal_ids:
                if not self.svg_has_element_with_id(terminal_id):
                    print(f"Connector {connector_id} references missing terminal {terminal_id} in SVG")
                    errors += 1
        return errors

    def svg_has_element_with_id(self, element_id):
        # Implement this method to check if the referenced SVG has an element with the given ID
        pass

    @staticmethod
    def get_name():
        return "connector_terminal"

    @staticmethod
    def get_description():
        return "Check if the connector terminals defined in the FZP file exist in the referenced SVGs"

