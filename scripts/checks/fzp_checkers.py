import os
from lxml import etree
from abc import ABC, abstractmethod
from .fzp_utils import FZPUtils
from .svg_utils import SVGUtils
import re
import logging
import datetime


class ValidationIssue:
    """Represents a validation issue with node reference"""
    
    def __init__(self, message, severity='error', node=None):
        self.message = message
        self.severity = severity
        self.node = node

class FixResult:
    """Represents a fix that was applied during checking"""
    
    def __init__(self, message, node=None, line_number=None):
        self.message = message
        self.node = node
        self.line_number = line_number

class FZPChecker(ABC):
    def __init__(self, fzp_doc):
        self.fzp_doc = fzp_doc
        self.issues = []
        self.fixes = []
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def check(self):
        pass

    def add_error(self, message, node=None):
        issue = ValidationIssue(message, severity='error', node=node)
        self.issues.append(issue)
        self.logger.debug(f"Error: {message}")

    def add_warning(self, message, node=None):
        issue = ValidationIssue(message, severity='warning', node=node)
        self.issues.append(issue)
        self.logger.debug(f"Warning: {message}")

    def add_fix(self, message, node=None, line_number=None):
        fix = FixResult(message, node=node, line_number=line_number)
        self.fixes.append(fix)
        self.logger.debug(f"Fixed: {message}")

    def get_result(self):
        errors = len([i for i in self.issues if i.severity == 'error'])
        warnings = len([i for i in self.issues if i.severity == 'warning'])
        return errors, warnings
    
    def get_fixes_count(self):
        return len(self.fixes)

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
        root = self.fzp_doc.getroot()
        for tag in required_tags:
            elements = self.fzp_doc.xpath(f"//{tag}")
            if not elements:
                self.add_error(f"Missing required tag: {tag}", node=root)
        return self.get_result()

    @staticmethod
    def get_name():
        return "missing_tags"

    @staticmethod
    def get_description():
        return "Check for missing required tags in the FZP file"


class FZPConnectorTerminalChecker(FZPChecker):
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

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
            self.add_error(f"Connector '{connector_id}' references missing terminal '{terminal_id}' in SVG", node=p_element)
        return self.get_result()

    def svg_has_element_with_id(self, element_id, view_name):
        svg_doc = self.svg_docs.get(view_name)
        if not svg_doc:
            return True  # Skip if SVG not available
        try:
            elements = svg_doc.xpath(f"//*[@id='{element_id}']")
            return len(elements) > 0
        except Exception as e:
            print(f"Error processing {view_name} SVG: {str(e)}")
            return True  # Not a 'missing element' if there's an error
        return False

    def fix(self, filename):
        """
        Removes invalid terminalId attributes from the FZP XML.

        Args:
            filename: Path to the FZP file to write fixes to

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
            # Create a backup before modifying
            backup_path = filename + ".bak"
            if not os.path.exists(backup_path):
                self.fzp_doc.write(backup_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                print(f"Backup created at '{backup_path}'.")

            # Write the modified XML back to the FZP file
            self.fzp_doc.write(filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')
            print(f"FZP file '{filename}' has been updated successfully.")
            return True
        else:
            print("No invalid terminal IDs found. No changes made.")
            return False

    @staticmethod
    def get_name():
        return "connector_terminal"

    @staticmethod
    def get_description():
        return "Check if the connector terminals defined in the FZP file exist in the referenced SVGs"


class FZPConnectorSvgRefChecker(FZPChecker):
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

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
                        # Skip legs
                        if 'legId' in p.attrib:
                            continue
                        # Skip hybrids or unknown layers
                        if FZPUtils.is_hybrid_or_unknown_layer(p):
                            continue

                        connector_svg_id = p.attrib.get("svgId")
                        layer = p.attrib.get("layer")
                        if not connector_svg_id:
                            self.add_error(f"Connector {connector_id} does not reference an element in layer {layer}.")
        return self.get_result()

    @staticmethod
    def get_name():
        return "connector_svg_ref"

    @staticmethod
    def get_description():
        return "Check if connectors reference SVG elements via svgId attribute"


class FZPPCBConnectorStrokeChecker(FZPChecker):
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

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

                        if not self.is_connector_stroke_valid(view.tag, connector_svg_id):
                            self.add_error(f"Invalid stroke for connector '{connector_svg_id}' in PCB view")
        return self.get_result()

    def is_connector_stroke_valid(self, view_name, connector_id):
        svg_doc = self.svg_docs.get(view_name)
        if not svg_doc:
            return True

        try:
            elements = svg_doc.xpath(f"//*[@id='{connector_id}']")
            if elements:
                try:
                    return SVGUtils.has_valid_stroke(elements[0])
                except ValueError as e:
                    self.add_error(f"Failure with {connector_id}: {e}")
                    return True # Connector not found, skip further checks
            else:
                self.add_error(f"Connector {connector_id} not found in {view_name} SVG")
                return True
        except Exception as e:
            self.add_error(f"Error processing {view_name} SVG: {str(e)}")
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
        root = self.fzp_doc.getroot()
        version = root.get('fritzingVersion')
        if not version:
            self.add_error("'FritzingVersion' is undefined or empty.", node=root)
        else:
            # Requires a Fritzing release version as announced on the blog or download page.
            version_pattern = r'^\d+\.\d+\.\d+.*$'
            if not re.match(version_pattern, version.strip()):
                self.add_error(f"'FritzingVersion' '{version}' should be in semantic versioning format (https://semver.org/).", node=root)
        return self.get_result()

    @staticmethod
    def get_name():
        return "fritzing_version"

    @staticmethod
    def get_description():
        return "Check fritzing version attribute is present and valid"


class FZPFritzingVersionRangeChecker(FZPChecker):
    """Check that fritzingVersion is not too old."""

    @staticmethod
    def _parse_version(version_str):
        """Parse a version string into a comparable tuple of ints.

        Handles formats like '0.9.3b', '0.5.2b.02.18.4756', '1.0.3'.
        Only the first three numeric components are compared.
        """
        if not version_str:
            return None
        parts = version_str.strip().split('.')
        result = []
        for part in parts[:3]:
            digits = re.match(r'(\d+)', part)
            if digits:
                result.append(int(digits.group(1)))
            else:
                break
        if len(result) < 3:
            result.extend([0] * (3 - len(result)))
        return tuple(result[:3])

    def check(self):
        root = self.fzp_doc.getroot()
        version_str = root.get('fritzingVersion')
        if not version_str:
            # Missing version is handled by FZPFritzingVersionChecker
            return self.get_result()

        version = self._parse_version(version_str)
        if version is None:
            return self.get_result()

        if version < (0, 8, 0):
            self.add_error(
                f"fritzingVersion '{version_str}' is below 0.8. "
                f"This part is very old and likely needs a full update.",
                node=root
            )
        if version < (0, 9, 4):
            self.add_warning(
                f"fritzingVersion '{version_str}' — this part claims a fritzingVersion that is more than ten years old.",
                node=root
            )
        elif version < (1, 0, 4):
            self.add_warning(
                f"fritzingVersion '{version_str}' — this part might use some outdated conventions.",
                node=root
            )
        return self.get_result()

    @staticmethod
    def get_name():
        return "fritzing_version_range"

    @staticmethod
    def get_description():
        return "Check that fritzingVersion is not too old (error if < 0.8, warning if < 0.9.4 or < 1.0.4)"


class FZPModuleIDChecker(FZPChecker):
    def check(self):
        root = self.fzp_doc.getroot()
        module_id = root.get('moduleId')
        if not module_id:
            self.add_error("'ModuleID' is undefined or empty.", node=root)
        return self.get_result()

    @staticmethod
    def get_name():
        return "module_id"

    @staticmethod
    def get_description():
        return "Check module ID attribute is present"

class FZPModuleIDSpecialCharsChecker(FZPChecker):
    # Characters that are unsafe for filenames on Windows, Linux, or macOS
    FILENAME_UNSAFE_CHARS = set('<>:"/\\|?*\0')
    # Control characters (0x00-0x1F)
    CONTROL_CHARS = set(chr(c) for c in range(0, 32))
    MIN_LENGTH = 8

    def check(self):
        root = self.fzp_doc.getroot()
        module_id = root.get('moduleId')
        if not module_id:
            return self.get_result()

        if len(module_id) < self.MIN_LENGTH:
            self.add_error(f"ModuleID '{module_id}' is too short (minimum {self.MIN_LENGTH} characters)", node=root)

        reported_errors = set()
        reported_warnings = set()

        for char in module_id:
            if char in self.CONTROL_CHARS or char in self.FILENAME_UNSAFE_CHARS:
                if char not in reported_errors:
                    reported_errors.add(char)
                    if ord(char) < 32:
                        self.add_error(f"ModuleID contains control character 0x{ord(char):02X} which is unsafe for filenames", node=root)
                    else:
                        self.add_error(f"ModuleID contains character '{char}' which is unsafe for filenames", node=root)
            elif not (char.isalnum() or char in '-_.'):
                if char not in reported_warnings:
                    reported_warnings.add(char)
                    if char == ' ':
                        self.add_warning("ModuleID contains spaces", node=root)
                    else:
                        self.add_warning(f"ModuleID contains non-alphanumeric character '{char}'", node=root)

        return self.get_result()

    def fix(self, filename):
        """Replace unsafe characters in moduleId with underscores."""
        with open(filename, 'r', encoding='UTF-8') as f:
            content = f.read()

        original_content = content

        pattern = r'(moduleId\s*=\s*")([^"]*?)(")'

        def replace_module_id(match):
            prefix = match.group(1)
            module_id = match.group(2)
            suffix = match.group(3)

            sanitized = []
            for char in module_id:
                if char.isalnum() or char in '-_.':
                    sanitized.append(char)
                else:
                    sanitized.append('_')
            sanitized = ''.join(sanitized)

            if sanitized != module_id:
                self.add_fix(f"Sanitized moduleId from '{module_id}' to '{sanitized}'")
                return f"{prefix}{sanitized}{suffix}"
            return match.group(0)

        content = re.sub(pattern, replace_module_id, content)

        if content != original_content:
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(content)

        return self.fixes

    @staticmethod
    def get_name():
        return "module_id_special_chars"

    @staticmethod
    def get_description():
        return "Check module ID for characters that are unsafe for filenames or not alphanumeric"


class FZPVersionChecker(FZPChecker):
    def check(self):
        version_elements = self.fzp_doc.xpath("//version")
        if not version_elements:
            self.add_warning("'Version' is undefined.", node=self.fzp_doc.getroot())
        else:
            version_element = version_elements[0]
            version = version_element.text
            if not re.match(r'^\d+(\.\d+)*$', version):
                self.add_warning(f"'Version' '{version}' does not match the expected format.", node=version_element)
        return self.get_result()

    @staticmethod
    def get_name():
        return "version"

    @staticmethod
    def get_description():
        return "Check version tag is present and valid"


class FZPTitleChecker(FZPChecker):
    def check(self):
        title_elements = self.fzp_doc.xpath("//title")
        if not title_elements:
            self.add_error("'Title' is undefined or empty.", node=self.fzp_doc.getroot())
        return self.get_result()

    @staticmethod
    def get_name():
        return "title"

    @staticmethod
    def get_description():
        return "Check title tag is present"


class FZPDescriptionChecker(FZPChecker):
    def check(self):
        description_elements = self.fzp_doc.xpath("//description")
        if not description_elements:
            self.add_warning("'Description' is undefined.", node=self.fzp_doc.getroot())
        return self.get_result()

    @staticmethod
    def get_name():
        return "description"

    @staticmethod
    def get_description():
        return "Check description tag is present"


class FZPAuthorChecker(FZPChecker):
    def check(self):
        author_elements = self.fzp_doc.xpath("//author")
        if not author_elements:
            self.add_warning("'Author' is undefined.", node=self.fzp_doc.getroot())
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
            self.add_error("'views' section is missing.", node=self.fzp_doc.getroot())
            return self.get_result()

        views_element = views[0]
        required_views = ['breadboardView', 'pcbView', 'schematicView']
        for view in required_views:
            if not views_element.xpath(f".//{view}"):
                self.add_error(f"Required view '{view}' is missing.", node=views_element)
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
                self.add_error(f"Bus with missing ID found: {etree.tostring(bus, pretty_print=True).decode()}", node=bus)
        return self.get_result()

    @staticmethod
    def get_name():
        return "bus_id"

    @staticmethod
    def get_description():
        return "Check bus IDs are present"


class FZPBusNodesChecker(FZPChecker):
    def __init__(self, fzp_doc):
        super().__init__(fzp_doc)
        self.buses_with_no_nodes = []

    def check(self):
        buses = self.fzp_doc.xpath("//bus")
        for bus in buses:
            nodes = bus.xpath(".//nodeMember")
            if not nodes:
                bus_id = bus.get('id', 'unknown')
                self.add_error(f"Bus '{bus_id}' has no node members.", node=bus)
                self.buses_with_no_nodes.append(bus_id)
            else:
                for node in nodes:
                    if not node.get('connectorId'):
                        bus_id = bus.get('id', 'unknown')
                        self.add_error(f"Node missing connectorId in Bus '{bus_id}'.", node=node)
        return self.get_result()

    def fix(self, filename):
        """Remove buses that have no node members by treating XML as string and removing the relevant blocks."""
        if not self.buses_with_no_nodes:
            return False  # Nothing to fix

        fixed = False

        with open(filename, 'r', encoding='UTF-8') as f:
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
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(content)

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
                    self.add_error(f"ConnectorLayer missing 'layer' ID in Connector '{connector_id}'.", node=layer)
                if not layer.get('svgId'):
                    self.add_error(f"ConnectorLayer missing 'svgId' in Connector '{connector_id}'.", node=layer)
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
                    self.add_error("'family' property has no value.", node=prop)
                return self.get_result()
        self.add_error("'family' property is missing.", node=self.fzp_doc.getroot())
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
                self.add_error(f"Duplicate property name found: '{name}'.", node=prop)
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
                self.add_error(f"Property with empty 'name' attribute found: {etree.tostring(prop, pretty_print=True).decode()}", node=prop)
            elif not prop.text:
                self.add_error(f"Property '{name}' has an empty value.", node=prop)
        return self.get_result()

    def fix(self, filename):
        """Apply fixes for property issues using regex to avoid etree side effects."""
        filename_base = os.path.basename(filename).lower()

        # Determine manufacturer from filename (case-insensitive)
        manufacturer = None
        if "adafruit" in filename_base:
            manufacturer = "Adafruit"
        elif "infineon" in filename_base:
            manufacturer = "Infineon"
        elif "arduino" in filename_base:
            manufacturer = "Arduino"
        elif "sparkfun" in filename_base:
            manufacturer = "SparkFun"
        elif "espressif" in filename_base:
            manufacturer = "Espressif"

        with open(filename, 'r', encoding='UTF-8') as f:
            content = f.read()

        original_content = content

        # Remove empty layer properties
        empty_layer_pattern = r'[\t ]*<property name="layer">\s*</property>\r?\n?'
        new_content, layer_removals = re.subn(empty_layer_pattern, '', content)
        if layer_removals > 0:
            self.add_fix(f"Removed {layer_removals} empty 'layer' property/properties")
            content = new_content

        if manufacturer:
            # Set empty mn property to detected manufacturer
            empty_mn_pattern = r'(<property name="mn">)\s*(</property>)'
            mn_replacement = rf'\1{manufacturer}\2'
            new_content, mn_fixes = re.subn(empty_mn_pattern, mn_replacement, content)
            if mn_fixes > 0:
                self.add_fix(f"Set empty 'mn' property to '{manufacturer}'")
                content = new_content

        # Find part number value to set mpn (if empty)
        part_number_match = re.search(r'<property name="part number">([^<]+)</property>', content)
        if part_number_match:
            part_number_value = part_number_match.group(1).strip()

            # Set empty mpn property to part number value
            empty_mpn_pattern = r'<property name="mpn">\s*</property>'
            mpn_replacement = f'<property name="mpn">{part_number_value}</property>'
            new_content, mpn_fixes = re.subn(empty_mpn_pattern, mpn_replacement, content)
            if mpn_fixes > 0:
                self.add_fix(f"Set 'mpn' property to '{part_number_value}' from 'part number'")
                content = new_content

        # Write back if modified
        if content != original_content:
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(content)
            return True

        return False

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
                        self.add_error(f"Tag '{element}' is missing required attribute '{attr}'.", node=elements[0])

        # Check required tags
        for tag in required_tags:
            if not self.fzp_doc.xpath(f"//{tag}"):
                self.add_error(f"Required tag '{tag}' is missing.", node=self.fzp_doc.getroot())

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
    def __init__(self, fzp_doc, svg_docs):
        super().__init__(fzp_doc)
        self.svg_docs = svg_docs

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

            svg_doc = self.svg_docs.get(view.tag)
            if not svg_doc:
                continue  # Skip if SVG not available

            # Check each layer ID
            layer_elements = layers.xpath("layer")
            for layer_element in layer_elements:
                layer_id = layer_element.get("layerId")
                if not layer_id:
                    continue

                # Look for matching ID in SVG
                matching_elements = svg_doc.xpath(f"//*[@id='{layer_id}']")
                if not matching_elements:
                    self.add_error(f"Layer ID '{layer_id}' from {view.tag} not found in SVG")

        return self.get_result()

    @staticmethod
    def get_name():
        return "layer_ids"

    @staticmethod
    def get_description():
        return "Check that layer IDs in FZP file match with IDs in corresponding SVG files"


class FZPDateFormatChecker(FZPChecker):
    """Checker for date format validation and automatic fixing"""

    def __init__(self, fzp_doc):
        super().__init__(fzp_doc)

    def check(self):
        """Check date format in FZP file"""
        # Find all date elements
        date_elements = self.fzp_doc.xpath("//date")

        for date_element in date_elements:
            if date_element.text is None or not date_element.text.strip():
                self.add_warning("Date element is empty", node=date_element)
                continue

            date_text = date_element.text.strip()

            # Try to parse as ISO format first (this is the target format)
            try:
                datetime.date.fromisoformat(date_text)
                # If successful, date is already in correct format
                continue
            except ValueError:
                pass

            # Try to parse and fix common date formats
            converted_date = self._try_convert_date_format(date_text)

            if converted_date:
                # Report the issue - fix method will handle the actual fixing
                self.add_warning(f"Date format '{date_text}' should be in YYYY-MM-DD format. Can be converted to: '{converted_date}'",
                               node=date_element)
            else:
                # Unable to parse the date
                self.add_error(f"Invalid date format: '{date_text}'. Expected YYYY-MM-DD format.",
                             node=date_element)

        return self.get_result()

    def fix(self, filename):
        """Apply date format fixes using regex to avoid etree side effects"""
        with open(filename, 'r', encoding='UTF-8') as f:
            content = f.read()

        original_content = content

        # Apply date format conversions using regex
        fixes_applied = 0

        # Pattern to match date elements
        date_pattern = r'(<date>)(.*?)(</date>)'

        def date_replacer(match):
            nonlocal fixes_applied
            date_text = match.group(2).strip()

            # Skip if already in ISO format
            try:
                datetime.date.fromisoformat(date_text)
                return match.group(0)  # Return unchanged
            except ValueError:
                pass

            # Try to convert the date
            converted_date = self._try_convert_date_format(date_text)
            if converted_date:
                fixes_applied += 1
                self.add_fix(f"Converted date format from '{date_text}' to '{converted_date}'")
                return f"{match.group(1)}{converted_date}{match.group(3)}"

            return match.group(0)  # Return unchanged if can't convert

        new_content = re.sub(date_pattern, date_replacer, content)

        # Write back if changes were made
        if new_content != original_content:
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(new_content)

        return self.fixes

    def _try_convert_date_format(self, date_text):
        """Try to convert various date formats to ISO format (YYYY-MM-DD)"""

        # Common date format patterns and their conversion logic
        date_patterns = [
            # Format: "Thu Jun 13 2024" or "Jun 13 2024" (with optional day name)
            {
                'pattern': r'^(?:\w{3}\s+)?(\w{3})\s+(\d{1,2})\s+(\d{4})$',
                'months': {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                    'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                },
                'converter': self._convert_month_day_year
            },

            # Format: "13/06/2024" or "13-06-2024" (ambiguous DD/MM/YYYY vs MM/DD/YYYY)
            # We'll try both interpretations and use the valid one
            {
                'pattern': r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$',
                'converter': self._convert_ambiguous_date
            },

            # Format: "2024/06/13" or "2024-06-13" (YYYY/MM/DD or YYYY-MM-DD with wrong separator)
            {
                'pattern': r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$',
                'converter': self._convert_yyyy_mm_dd_fix_separator
            },

            # Japanese format: "木 3 31 2016" (from importer)
            {
                'pattern': r'^木\s+(\d+)\s+(\d+)\s+(\d+)$',
                'converter': self._convert_japanese_format
            }
        ]

        for pattern_info in date_patterns:
            match = re.match(pattern_info['pattern'], date_text)
            if match:
                try:
                    return pattern_info['converter'](match, pattern_info.get('months'))
                except (ValueError, KeyError):
                    continue

        return None

    def _convert_month_day_year(self, match, months_dict):
        """Convert 'Thu Jun 13 2024' or 'Jun 13 2024' format"""
        month_name = match.group(1)
        day = int(match.group(2))
        year = int(match.group(3))

        if month_name not in months_dict:
            raise ValueError(f"Unknown month: {month_name}")

        month = months_dict[month_name]
        return f"{year:04d}-{month}-{day:02d}"

    def _convert_ambiguous_date(self, match, months_dict=None):
        """Convert DD/MM/YYYY or MM/DD/YYYY format - try both interpretations"""
        first_num = int(match.group(1))
        second_num = int(match.group(2))
        year = int(match.group(3))

        # Try DD/MM/YYYY first (European format)
        if 1 <= second_num <= 12 and 1 <= first_num <= 31:
            day, month = first_num, second_num
            # Additional validation: check for obviously wrong dates
            if day > 12 and month <= 12:
                # Definitely DD/MM format (e.g., 25/06/2024)
                return f"{year:04d}-{month:02d}-{day:02d}"

        # Try MM/DD/YYYY (US format)
        if 1 <= first_num <= 12 and 1 <= second_num <= 31:
            month, day = first_num, second_num
            # Additional validation: check for obviously wrong dates
            if first_num > 12:
                # Can't be MM/DD format
                raise ValueError("Invalid date format")
            elif second_num > 12:
                # Must be MM/DD format (e.g., 06/25/2024)
                return f"{year:04d}-{month:02d}-{day:02d}"

        # If both are valid (ambiguous case like 05/06/2024), default to DD/MM
        if 1 <= second_num <= 12 and 1 <= first_num <= 12:
            day, month = first_num, second_num
            return f"{year:04d}-{month:02d}-{day:02d}"

        raise ValueError("Invalid day or month")

    def _convert_yyyy_mm_dd_fix_separator(self, match, months_dict=None):
        """Convert YYYY/MM/DD or YYYY-MM-DD with wrong separator to YYYY-MM-DD"""
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        if not (1 <= month <= 12) or not (1 <= day <= 31):
            raise ValueError("Invalid day or month")

        return f"{year:04d}-{month:02d}-{day:02d}"

    def _convert_japanese_format(self, match, months_dict=None):
        """Convert Japanese format '木 3 31 2016' to ISO format"""
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))

        if not (1 <= month <= 12) or not (1 <= day <= 31):
            raise ValueError("Invalid day or month")

        return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def get_name():
        return "date_format"

    @staticmethod
    def get_description():
        return "Check and fix date format in FZP files. Supports multiple common date formats and converts them to ISO format (YYYY-MM-DD)"
