import os
from lxml import etree
from abc import ABC, abstractmethod
from fzp_utils import FZPUtils
from svg_utils import SVGUtils
from fzp_additional_checks import (
      check_fritzing_version,
      check_module_id,
      check_version,
      check_title,
      check_description,
      check_author,
      check_views,
      check_bus_id,
      check_bus_nodes,
      check_connector_layers,
      check_family_property,
      check_unique_property_names,
      check_property_fields,
      check_required_tags_and_attributes,
      check_buses
  )

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

class FZPFritzingVersionChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "fritzing_version"

    @staticmethod
    def get_description():
        return "Check fritzing version attribute is present and valid"

    def check(self):
        return check_fritzing_version(self.fzp_doc)

class FZPModuleIDChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "module_id"

    @staticmethod
    def get_description():
        return "Check module ID attribute is present"

    def check(self):
        return check_module_id(self.fzp_doc)

class FZPVersionChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "version"

    @staticmethod
    def get_description():
        return "Check version tag is present and valid"

    def check(self):
        return check_version(self.fzp_doc)

class FZPTitleChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "title"

    @staticmethod
    def get_description():
        return "Check title tag is present"

    def check(self):
        return check_title(self.fzp_doc)

class FZPDescriptionChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "description"

    @staticmethod
    def get_description():
        return "Check description tag is present"

    def check(self):
        return check_description(self.fzp_doc)

class FZPAuthorChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "author"

    @staticmethod
    def get_description():
        return "Check author tag is present"

    def check(self):
        return check_author(self.fzp_doc)

class FZPViewsChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "views"

    @staticmethod
    def get_description():
        return "Check views section is present"

    def check(self):
        return check_views(self.fzp_doc)

class FZPBusIDChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "bus_id"

    @staticmethod
    def get_description():
        return "Check bus IDs are present"

    def check(self):
        return check_bus_id(self.fzp_doc)

class FZPBusNodesChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "bus_nodes"

    @staticmethod
    def get_description():
        return "Check bus nodes are present and valid"

    def check(self):
        return check_bus_nodes(self.fzp_doc)

class FZPConnectorLayersChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "connector_layers"

    @staticmethod
    def get_description():
        return "Check connector layers are properly defined"

    def check(self):
        return check_connector_layers(self.fzp_doc)

class FZPFamilyPropertyChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "family_property"

    @staticmethod
    def get_description():
        return "Check family property is present"

    def check(self):
        return check_family_property(self.fzp_doc)

class FZPUniquePropertyNamesChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "unique_property_names"

    @staticmethod
    def get_description():
        return "Check property names are unique"

    def check(self):
        return check_unique_property_names(self.fzp_doc)

class FZPPropertyFieldsChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "property_fields"

    @staticmethod
    def get_description():
        return "Check property fields are properly defined"

    def check(self):
        return check_property_fields(self.fzp_doc)

class FZPRequiredTagsChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "required_tags"

    @staticmethod
    def get_description():
        return "Check all required tags and attributes are present"

    def check(self):
        return check_required_tags_and_attributes(self.fzp_doc)

class FZPBusesChecker(FZPChecker):
    @staticmethod
    def get_name():
        return "buses"

    @staticmethod
    def get_description():
        return "Check buses are properly defined"

    def check(self):
        return check_buses(self.fzp_doc)
