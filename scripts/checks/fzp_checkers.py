import os
from lxml import etree
from abc import ABC, abstractmethod
from fzp_utils import FZPUtils
from svg_utils import SVGUtils
import re

class FZPChecker(ABC):
    needs_path = False

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

    def _find_invalid_terminal_ids(self):
        """
        Private helper method to find invalid terminal IDs in connectors.

        Yields:
            Tuple containing:
                - connector Element
                - p Element with missing terminalId
                - terminal_id string
        """
        connectors_section = self.fzp_doc.xpath("//module/connectors")
        if not connectors_section:
            print("No connectors section found in the FZP file.")
            return

        connectors = connectors_section[0].xpath("connector")
        for connector in connectors:
            connector_id = connector.attrib.get("id", "unknown")
            views = connector.xpath("views")
            if not views:
                continue
            views = views[0]
            for view in views:
                if view.tag != "schematicView":
                    continue

                p_elements = view.xpath("p[@terminalId]")
                for p in p_elements:
                    terminal_id = p.attrib.get("terminalId")
                    if not self.svg_has_element_with_id(terminal_id, view.tag):
                        yield (connector, p, terminal_id, connector_id)

    def check(self):
        for connector, p_element, terminal_id, connector_id in self._find_invalid_terminal_ids():
            self.add_error(f"Connector '{connector_id}' references missing terminal '{terminal_id}' in SVG")
        return self.get_result()

    def svg_has_element_with_id(self, element_id, view_name):
        svg_path = FZPUtils.get_svg_path_from_view(self.fzp_doc, self.fzp_path, view_name)
        if not svg_path:
            return True  # Skip template SVGs
        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{element_id}']")
            return len(elements) > 0
        except (FileNotFoundError, OSError) as e:
            print(f"SVG file error: {svg_path} - {str(e)}")
            return True  # Not a 'missing element' if the complete file is missing
        except etree.XMLSyntaxError as err:
            print(f"Error parsing SVG file: {svg_path}")
            print(str(err))
        return False

    def fix(self):
        """
        Removes invalid terminalId attributes from the FZP XML.

        Returns:
            bool: True if modifications were made and saved successfully, False otherwise.
        """
        modified = False

        for connector, p_element, terminal_id, connector_id in self._find_invalid_terminal_ids():
            # Remove the terminalId attribute
            del p_element.attrib["terminalId"]
            print(f"Removed missing terminalId '{terminal_id}' from connector '{connector_id}' in schematicView.")
            modified = True

        if modified:
            try:
                # Create a backup before modifying
                backup_path = self.fzp_path + ".bak"
                if not os.path.exists(backup_path):
                    self.fzp_doc.write(backup_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                    print(f"Backup created at '{backup_path}'.")

                # Write the modified XML back to the FZP file
                self.fzp_doc.write(self.fzp_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                print(f"FZP file '{self.fzp_path}' has been updated successfully.")
                return True
            except Exception as e:
                print(f"Failed to write FZP file '{self.fzp_path}': {str(e)}")
                return False
        else:
            print("No invalid terminal IDs found. No changes made.")
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
                        # Skip legs, connector is invisible
                        if 'legId' in p.attrib:
                            continue
                        # Skip hybrids or unknown layers, no way to check visibility
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
                        if not self.is_connector_visible(svg_path, connector_svg_id): # we already checked that it is not hybrid
                            self.add_error(f"Invisible connector '{connector_svg_id}' in layer '{layer}' of file '{self.fzp_path}'")
        return self.get_result()

    def is_connector_visible(self, svg_path, connector_id):
        if not os.path.isfile(svg_path):
            self.add_warning(f"Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True # Skip the check if the SVG path is invalid

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
            self.add_warning(f"Invalid SVG path '{svg_path}' for connector '{connector_id}'")
            return True

        try:
            svg_doc = etree.parse(svg_path)
            elements = svg_doc.xpath(f"//*[@id='{connector_id}']")
            if elements:
                try:
                    return SVGUtils.has_valid_stroke(elements[0])
                except ValueError as e:
                    self.add_error(f"Failure with {connector_id}: {e}")
                    return True # Connector not found, skip further checks
            else:
                self.add_error(f"Connector {connector_id} not found in {svg_path}")
                return True
        except FileNotFoundError:
            self.add_error(f"SVG file not found: {svg_path}")
            return True
        except etree.XMLSyntaxError as err:
            self.add_error(f"Failed to parse SVG file: {svg_path}")
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
        else:
            # Requires a Fritzing release version as announced on the blog or download page.
            version_pattern = r'^\d+\.\d+\.\d+.*$'
            if not re.match(version_pattern, version.strip()):
                self.add_error(f"'FritzingVersion' '{version}' should be in semantic versioning format (https://semver.org/).")
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

class FZPModuleIDSpecialCharsChecker(FZPChecker):
    def check(self):
        module_id = self.fzp_doc.getroot().get('moduleId')
        if module_id:
            special_chars = ['*', '?', ',', '/']
            for char in special_chars:
                if char in module_id:
                    self.add_warning(f"ModuleID contains special character '{char}' which may cause issues")
        return self.get_result()

    @staticmethod
    def get_name():
        return "module_id_special_chars"

    @staticmethod
    def get_description():
        return "Check module ID for special characters that may cause issues"


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
    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path
        self.buses_with_no_nodes = []

    def check(self):
        buses = self.fzp_doc.xpath("//bus")
        for bus in buses:
            nodes = bus.xpath(".//nodeMember")
            if not nodes:
                bus_id = bus.get('id', 'unknown')
                self.add_error(f"Bus '{bus_id}' has no node members.")
                self.buses_with_no_nodes.append(bus_id)
            else:
                for node in nodes:
                    if not node.get('connectorId'):
                        bus_id = bus.get('id', 'unknown')
                        self.add_error(f"Node missing connectorId in Bus '{bus_id}'.")
        return self.get_result()

    def fix(self):
        """Remove buses that have no node members by treating XML as string and removing the relevant blocks."""
        if not self.buses_with_no_nodes:
            return False  # Nothing to fix

        fixed = False

        try:
            with open(self.fzp_path, 'r', encoding='UTF-8') as f:
                content = f.read()

            for bus_id in self.buses_with_no_nodes:
                # Pattern includes leading whitespace and entire line
                pattern = re.compile(
                    r'[\t ]*<bus\b[^>]*\bid\s*=\s*["\']{}["\'][^>]*/?>(?:[^<]*</bus>)?\r?\n'.format(re.escape(bus_id))
                )
                new_content, count = pattern.subn('', content)
                if count > 0:
                    fixed = True
                    print(f"Fixed: Removed empty bus '{bus_id}'")
                content = new_content

            if fixed:
                with open(self.fzp_path, 'w', encoding='UTF-8') as f:
                    f.write(content)

        except Exception as e:
            self.add_error(f"Failed while fixing buses: {str(e)}")
            return False

        return fixed

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
        required_tags = ['title', 'tags', 'properties', 'views', 'connectors']

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

class FZPLayerIDsChecker(FZPChecker):
    def __init__(self, fzp_doc, fzp_path):
        super().__init__(fzp_doc)
        self.fzp_path = fzp_path

    def check(self):
        views = self.fzp_doc.xpath("//views")[0]
        for view in views:
            if view.tag == "defaultUnits":
                continue

            layers_elements = view.xpath("layers")
            if not layers_elements:
                continue

            layers = layers_elements[0]
            image = layers.get("image")
            if not image:
                continue

            svg_path = FZPUtils.get_svg_path(self.fzp_path, image, view.tag)
            if svg_path is None:
                continue  # Skip template SVGs

            if not os.path.isfile(svg_path):
                self.add_error(f"SVG file not found: {svg_path}")
                continue

            try:
                svg_doc = etree.parse(svg_path)

                # Check each layer ID
                layer_elements = layers.xpath("layer")
                for layer_element in layer_elements:
                    layer_id = layer_element.get("layerId")
                    if not layer_id:
                        continue

                    # Look for matching ID in SVG
                    matching_elements = svg_doc.xpath(f"//*[@id='{layer_id}']")
                    if not matching_elements:
                        self.add_error(f"Layer ID '{layer_id}' from {view.tag} not found in SVG file {svg_path}")

            except etree.XMLSyntaxError as err:
                self.add_error(f"Error parsing SVG file {svg_path}: {str(err)}")

        return self.get_result()

    @staticmethod
    def get_name():
        return "layer_ids"

    @staticmethod
    def get_description():
        return "Check that layer IDs in FZP file match with IDs in corresponding SVG files"
