import os
from lxml import etree
from abc import ABC, abstractmethod
from fzp_utils import FZPUtils
from svg_utils import SVGUtils
import re

class FZPChecker(ABC):
    def __init__(self, fzp_doc):
        self.fzp_doc = fzp_doc
        self.errors = 0
        self.warnings = 0

    @abstractmethod
    def check(self):
        pass

    def add_error(self, message):
        print(f"Error: {message}")
        self.errors += 1

    def add_warning(self, message):
        print(f"Warning: {message}")
        self.warnings += 1

    def get_result(self):
        return self.errors, self.warnings

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
        required_tags = ["module", "version", "author", "title", "label", "date", "description", "views", "connectors"]
        for tag in required_tags:
            if not self.fzp_doc.xpath(f"//{tag}"):
                self.add_error(f"Missing required tag: {tag}")
        return self.get_result()

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
                            self.add_error(f"Connector {connector_id} references missing terminal {terminal_id} in SVG")
        return self.get_result()

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
                            self.add_error(f"Connector {connector_id} does not reference an element in layer {layer}.")
                            continue

                        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, view.tag, layer)
                        if not svg_path:
                            continue  # Skip template SVGs
                        if not self.is_connector_visible(svg_path, connector_svg_id):
                            self.add_error(f"Invisible connector '{connector_svg_id}' in layer '{layer}' of file '{self.fzp_path}'")
        return self.get_result()

    def is_connector_visible(self, svg_path, connector_id):
        if not os.path.isfile(svg_path):
            print(f"Warning: Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True

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
                            self.add_error(f"Invalid stroke for connector '{connector_svg_id}' in PCB view of file '{self.fzp_path}'")
        return self.get_result()

    def is_connector_stroke_valid(self, svg_path, connector_id):
        if not os.path.isfile(svg_path):
            print(f"Warning: Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True

        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{connector_id}']")
            if elements:
                try:
                    return SVGUtils.has_valid_stroke(elements[0])
                except ValueError as e:
                    self.add_error(f"Error in {connector_id}: {e}")
                    return True
            else:
                self.add_error(f"Warning: Connector {connector_id} not found in {svg_path}")
                return True
        except FileNotFoundError:
            self.add_error(f"SVG file not found: {svg_path}")
            return True
        except etree.XMLSyntaxError as err:
            self.add_error(f"Error parsing SVG file: {svg_path}")
            print(str(err))
            return True
        return False

    @staticmethod
    def get_name():
        return "pcb_connector_stroke"

    @staticmethod
    def get_description():
        return "Check for valid stroke attributes in connectors of the PCB view in the SVG files referenced by the FZP"


class FZPFritzingVersionChecker(FZPChecker):
    def check(self):
        version = self.fzp_doc.getroot().get('fritzingVersion')
        if not version:
            self.add_error("'FritzingVersion' is undefined or empty.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "fritzing_version"

    @staticmethod
    def get_description():
        return "Check fritzing version attribute is present and valid"


class FZPModuleIDChecker(FZPChecker):
    def check(self):
        module_id = self.fzp_doc.getroot().get('moduleId')
        if not module_id:
            self.add_error("'ModuleID' is undefined or empty.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "module_id"

    @staticmethod
    def get_description():
        return "Check module ID attribute is present"


class FZPVersionChecker(FZPChecker):
    def check(self):
        version_elements = self.fzp_doc.xpath("//version")
        if not version_elements:
            self.add_warning("'Version' is undefined.")
        else:
            version = version_elements[0].text
            if not re.match(r'^\d+(\.\d+)*$', version):
                self.add_warning(f"'Version' '{version}' does not match the expected format.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "version"

    @staticmethod
    def get_description():
        return "Check version tag is present and valid"


class FZPTitleChecker(FZPChecker):
    def check(self):
        if not self.fzp_doc.xpath("//title"):
            self.add_error("'Title' is undefined or empty.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "title"

    @staticmethod
    def get_description():
        return "Check title tag is present"


class FZPDescriptionChecker(FZPChecker):
    def check(self):
        if not self.fzp_doc.xpath("//description"):
            self.add_warning("'Description' is undefined.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "description"

    @staticmethod
    def get_description():
        return "Check description tag is present"


class FZPAuthorChecker(FZPChecker):
    def check(self):
        if not self.fzp_doc.xpath("//author"):
            self.add_warning("'Author' is undefined.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "author"

    @staticmethod
    def get_description():
        return "Check author tag is present"


class FZPViewsChecker(FZPChecker):
    def check(self):
        views = self.fzp_doc.xpath("//views")
        if not views:
            self.add_error("'views' section is missing.")
            return self.get_result()

        required_views = ['breadboardView', 'pcbView', 'schematicView']
        for view in required_views:
            if not views[0].xpath(f".//{view}"):
                self.add_error(f"Required view '{view}' is missing.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "views"

    @staticmethod
    def get_description():
        return "Check views section is present"


class FZPBusIDChecker(FZPChecker):
    def check(self):
        buses = self.fzp_doc.xpath("//bus")
        for bus in buses:
            if not bus.get('id'):
                self.add_error(f"Bus with missing ID found: {etree.tostring(bus, pretty_print=True).decode()}")
        return self.get_result()

    @staticmethod
    def get_name():
        return "bus_id"

    @staticmethod
    def get_description():
        return "Check bus IDs are present"


class FZPBusNodesChecker(FZPChecker):
    def check(self):
        buses = self.fzp_doc.xpath("//bus")
        for bus in buses:
            nodes = bus.xpath(".//nodeMember")
            if not nodes:
                self.add_error(f"Bus '{bus.get('id')}' has no node members.")
            else:
                for node in nodes:
                    if not node.get('connectorId'):
                        self.add_error(f"Node missing connectorId in Bus '{bus.get('id')}'.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "bus_nodes"

    @staticmethod
    def get_description():
        return "Check bus nodes are present and valid"


class FZPConnectorLayersChecker(FZPChecker):
    def check(self):
        connectors = self.fzp_doc.xpath("//connector")
        for connector in connectors:
            connector_id = connector.get('id')
            layers = connector.xpath(".//ConnectorLayer")
            for layer in layers:
                if not layer.get('layer'):
                    self.add_error(f"ConnectorLayer missing 'layer' ID in Connector '{connector_id}'.")
                if not layer.get('svgId'):
                    self.add_error(f"ConnectorLayer missing 'svgId' in Connector '{connector_id}'.")
                if not layer.get('terminalId'):
                    self.add_error(f"ConnectorLayer missing 'terminalId' in Connector '{connector_id}'.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "connector_layers"

    @staticmethod
    def get_description():
        return "Check connector layers are properly defined"


class FZPFamilyPropertyChecker(FZPChecker):
    def check(self):
        properties = self.fzp_doc.xpath("//property")
        for prop in properties:
            if prop.get('name') == 'family':
                if not prop.text:
                    self.add_error("'family' property has no value.")
                return self.get_result()
        self.add_error("'family' property is missing.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "family_property"

    @staticmethod
    def get_description():
        return "Check family property is present"


class FZPUniquePropertyNamesChecker(FZPChecker):
    def check(self):
        properties = self.fzp_doc.xpath("//property")
        names = set()
        for prop in properties:
            name = prop.get('name')
            if name in names:
                self.add_error(f"Duplicate property name found: '{name}'.")
            else:
                names.add(name)
        return self.get_result()

    @staticmethod
    def get_name():
        return "unique_property_names"

    @staticmethod
    def get_description():
        return "Check property names are unique"


class FZPPropertyFieldsChecker(FZPChecker):
    def check(self):
        properties = self.fzp_doc.xpath("//property")
        for prop in properties:
            name = prop.get('name')
            if not name:
                self.add_error(f"Property with empty 'name' attribute found: {etree.tostring(prop, pretty_print=True).decode()}")
            elif not prop.text:
                self.add_error(f"Property '{name}' has an empty value.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "property_fields"

    @staticmethod
    def get_description():
        return "Check property fields are properly defined"


class FZPRequiredTagsChecker(FZPChecker):
    def check(self):
        required_attributes = {
            'module': ['moduleId']
        }
        required_tags = ['title', 'tags', 'properties', 'views', 'connectors', 'buses']

        # Check required attributes
        for element, attributes in required_attributes.items():
            elements = self.fzp_doc.xpath(f"//{element}")
            if elements:
                for attr in attributes:
                    if not elements[0].get(attr):
                        self.add_error(f"Tag '{element}' is missing required attribute '{attr}'.")

        # Check required tags
        for tag in required_tags:
            if not self.fzp_doc.xpath(f"//{tag}"):
                self.add_error(f"Required tag '{tag}' is missing.")

        return self.get_result()

    @staticmethod
    def get_name():
        return "required_tags"

    @staticmethod
    def get_description():
        return "Check all required tags and attributes are present"


class FZPBusesChecker(FZPChecker):
    def check(self):
        buses = self.fzp_doc.xpath("//bus")
        for bus in buses:
            bus_id = bus.get('id')
            if not bus_id:
                self.add_error(f"Bus found without an ID: {etree.tostring(bus, pretty_print=True).decode()}")

            node_members = bus.xpath(".//nodeMember")
            if not node_members:
                if bus_id:
                    self.add_error(f"Bus '{bus_id}' has no node members.")
                else:
                    self.add_error("Bus has no node members.")

        return self.get_result()

    @staticmethod
    def get_name():
        return "buses"

    @staticmethod
    def get_description():
        return "Check buses are properly defined"
