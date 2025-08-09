# Filename: svg_checkers.py
from lxml import etree
import re
import os
from .svg_utils import SVGUtils
from .fzp_checkers import ValidationIssue

class SVGChecker:
    def __init__(self, svg_doc, layer_ids):
        self.svg_doc = svg_doc
        self.layer_ids = layer_ids
        self.errors = 0
        self.warnings = 0
        self.issues = []

    def add_error(self, message, node=None):
        issue = ValidationIssue(message, severity='error', node=node)
        self.issues.append(issue)
        print(f"Error: {message}")
        self.errors += 1

    def add_warning(self, message, node=None):
        issue = ValidationIssue(message, severity='warning', node=node)
        self.issues.append(issue)
        print(f"Warning: {message}")
        self.warnings += 1

    def get_result(self):
        return self.errors, self.warnings

    def check(self):
        pass

    @staticmethod
    def get_name():
        raise NotImplementedError

    @staticmethod
    def get_description():
        raise NotImplementedError

class SVGFontSizeChecker(SVGChecker):

    def getChildXML(self, elem):
        out = ""
        if elem.text:
            out += elem.text
        for c in elem.iterchildren():
            if len(c) == 0:
                out += f"<{c.tag}/>"
            else:
                out += f"<{c.tag}>{self.getChildXML(c)}</{c.tag}>"
            if c.tail:
                out += c.tail
        return out


    def check_font_size(self, element):
        font_size = SVGUtils.get_inherited_attribute(element, "font-size")
        if font_size is None:
            if element.tag.endswith("text"):
                for child in element.iterchildren():
                    if child.tag.endswith("tspan"):
                        return self.check_font_size(child)
            content = self.getChildXML(element)
            self.add_error(f"No font size found for element [{content}]", node=element)
            return
        if not re.match(r"^\d+(\.\d+)?$", font_size):
            content = self.getChildXML(element)
            self.add_error(f"Invalid font size {font_size} unit in element: [{content}]", node=element)

    def check(self):
        text_elements = self.svg_doc.xpath("//*[local-name()='text' or local-name()='tspan']")
        for element in text_elements:
            self.check_font_size(element)
        return self.get_result()


    @staticmethod
    def get_name():
        return "font_size"


    @staticmethod
    def get_description():
        return "Check that the font-size attribute of each text element is a valid number"


class SVGFontTypeChecker(SVGChecker):
    VALID_FONTS = {
        'Noto Sans',
        'OCR-Fritzing-mono',
        'Droid Sans',  # deprecated, use Noto Sans instead
        'Droid Sans Mono',  # deprecated, use Noto Sans instead
        'OCRA',
        'Segment16C'
    }

    FONT_REPLACEMENTS = {
        'Segment16C Bold.ttf': 'Segment16C',
        'DroidSans-Bold': 'Noto Sans',
        'NotoSans-Regular': 'Noto Sans',
        'OCRAStd': 'OCR-Fritzing-mono',
        'OCRATributeW01 - Regular': 'OCR-Fritzing-mono',
        'ocra10': 'OCR-Fritzing-mono',
        'OCRATributeW01-Regular': 'OCR-Fritzing-mono',
        'OpenSans': 'Noto Sans',
        'ArialMT': 'default',
        'MyriadPro - Regular': 'default',
        'MyriadPro-Regular': 'default',
        'HelveticaNeueLTStd-Roman': 'default',
        'DroidSans - Bold': 'Noto Sans',
        'DroidSans': 'Noto Sans',
        "Droid": "Noto Sans",
        'Droid Sans Mono': 'default',
        'DroidSansMono': 'default',
        'Arial-BoldMT': 'Noto Sans',
        'EurostileLTStd': 'Noto Sans',
    }

    def __init__(self, svg_doc, layer_ids):
        super().__init__(svg_doc, layer_ids)
        self.is_pcb_view = 'copper' in layer_ids or 'silkscreen' in layer_ids
        self.default_font = 'OCR-Fritzing-mono' if self.is_pcb_view else 'Noto Sans'

    def has_inherited_style(self, element):
        """Check if element has an inherited style attribute"""
        return SVGUtils.get_inherited_attribute(element, "style") is not None

    def fix(self, filename):
        """
        Fixes invalid or missing font families in the SVG document using regex
        to preserve original formatting and make minimal changes.
        Always uses double quotes for consistency.
        
        Args:
            filename: Path to the SVG file to write fixes to
        """

        try:
            # Read the original file
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            modified = False
            original_content = content

            # Pattern to match font-family with any quote style
            pattern = r'font-family\s*=\s*["\']\'?([^\'">]+)\'?["\']'

            def replace_font(match):
                nonlocal modified
                font = match.group(1)
                if font in self.FONT_REPLACEMENTS:
                    new_font = self.FONT_REPLACEMENTS[font]
                    if new_font == 'default':
                        new_font = self.default_font
                    modified = True
                    print(f"Replacing font '{font}' with '{new_font}'")
                    # Always use double quotes
                    return f'font-family="{new_font}"'
                return match.group(0)

            # Make replacements
            content = re.sub(pattern, replace_font, content)

            if modified:
                # Create backup if it doesn't exist
                backup_path = filename + ".bak"
                if not os.path.exists(backup_path):
                    with open(backup_path, 'w', encoding='utf-8') as file:
                        file.write(original_content)
                    print(f"Backup created at '{backup_path}'")

                # Write modified content only if changes were made
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f"SVG file '{filename}' has been updated successfully")
                return True
            else:
                print("No fonts found to replace. No changes made.")
                return False

        except Exception as e:
            print(f"Failed to process SVG file: {str(e)}")
            return False

    def check_font_type(self, element):
        font_family = SVGUtils.get_inherited_attribute(element, "font-family")
        if font_family is None:
            if element.tag.endswith("text"):
                for child in element.iterchildren():
                    if child.tag.endswith("tspan"):
                        return self.check_font_type(child)
            content = self.getChildXML(element)
            self.add_error(f"No font family found for element [{content}]", node=element)
            return

        # Remove quotes if present
        font_family = font_family.strip('"\'')

        if font_family not in self.VALID_FONTS:
            content = self.getChildXML(element)
            self.add_error(f"Invalid font family '{font_family}' in element: [{content}]", node=element)

    def getChildXML(self, elem):
        out = ""
        if elem.text:
            out += elem.text
        for c in elem.iterchildren():
            if len(c) == 0:
                out += f"<{c.tag}/>"
            else:
                out += f"<{c.tag}>{self.getChildXML(c)}</{c.tag}>"
            if c.tail:
                out += c.tail
        return out

    def check(self):
        text_elements = self.svg_doc.xpath("//*[local-name()='text' or local-name()='tspan']")
        for element in text_elements:
            self.check_font_type(element)
        return self.get_result()

    @staticmethod
    def get_name():
        return "font_type"

    @staticmethod
    def get_description():
        return "Check that font-family attributes use only allowed fonts (Noto Sans, OCR-Fritzing-mono, DroidSans, OCRA)"


class SVGViewBoxChecker(SVGChecker):
    def check(self):
        # For icons, we don't really need a viewBox
        if self.layer_ids == ['icon']:
            return self.get_result()

        root_element = self.svg_doc.getroot()
        if "viewBox" in root_element.attrib:
            viewbox = root_element.attrib["viewBox"]
            if not re.match(r"^-?\d+(\.\d+)?( -?\d+(\.\d+)?){3}$", viewbox):
                self.add_error(f"Invalid viewBox attribute: {viewbox}", node=root_element)
        else:
            self.add_error("Missing viewBox attribute", node=root_element)
        return self.get_result()

    @staticmethod
    def get_name():
        return "viewbox"

    @staticmethod
    def get_description():
        return "Check that the viewBox attribute is valid"


class SVGIdsChecker(SVGChecker):
    def check(self):
        id_occurrences = {}
        elements_with_id = self.svg_doc.xpath("//*[@id]")
        
        # First pass: collect all occurrences
        for element in elements_with_id:
            element_id = element.attrib["id"]
            if element_id not in id_occurrences:
                id_occurrences[element_id] = []
            id_occurrences[element_id].append(element)
        
        # Second pass: report duplicates with enumeration
        for element_id, elements in id_occurrences.items():
            if len(elements) > 1:
                for i, element in enumerate(elements, 1):
                    self.add_error(f"Duplicate id attribute: {element_id} (occurrence {i} of {len(elements)})", node=element)
        
        return self.get_result()

    def fix(self):
        """Fix duplicate 'label' IDs by grouping consecutive text elements under <g> tags"""
        from lxml import etree

        # Find all text elements with id="label" in document order
        label_elements = self.svg_doc.xpath("//text[@id='label']")

        if len(label_elements) <= 1:
            return

        # Group consecutive elements
        consecutive_groups = self._find_consecutive_groups(label_elements)

        # Create <g> tags for each group of consecutive elements (in reverse order to maintain positions)
        for group in reversed(consecutive_groups):
            if len(group) > 1:
                self._create_label_group(group)

    def _find_consecutive_groups(self, elements):
        """Find groups of consecutive text elements in document order"""
        if not elements:
            return []

        # Get all elements in the document to determine order
        all_elements = self.svg_doc.xpath("//*")
        element_positions = {elem: i for i, elem in enumerate(all_elements)}

        # Sort label elements by their document position
        sorted_elements = sorted(elements, key=lambda x: element_positions.get(x, float('inf')))

        # Group consecutive elements
        groups = []
        current_group = [sorted_elements[0]]

        for i in range(1, len(sorted_elements)):
            curr_pos = element_positions.get(sorted_elements[i], float('inf'))
            prev_pos = element_positions.get(sorted_elements[i-1], float('inf'))

            # Check if elements are consecutive in document order
            consecutive = True
            for pos in range(prev_pos + 1, curr_pos):
                if pos < len(all_elements):
                    between_elem = all_elements[pos]
                    # If there's a text element with id="label" between them, they're not consecutive
                    if between_elem.tag == "text" and between_elem.get("id") == "label":
                        consecutive = False
                        break

            if consecutive:
                current_group.append(sorted_elements[i])
            else:
                groups.append(current_group)
                current_group = [sorted_elements[i]]

        groups.append(current_group)
        return groups

    def _create_label_group(self, text_elements):
        """Create a <g id='label'> containing the consecutive text elements"""
        from lxml import etree

        if not text_elements:
            return

        # Use the first element's parent and position
        first_element = text_elements[0]
        parent = first_element.getparent()
        if parent is None:
            return

        # Create a new <g> element with id="label"
        group_element = etree.Element("g")
        group_element.set("id", "label")

        # Find the position of the first text element
        insert_index = list(parent).index(first_element)

        # Remove the id attribute from all text elements and add them to the group
        for text_element in text_elements:
            # Remove the id attribute since the group will have it
            if "id" in text_element.attrib:
                del text_element.attrib["id"]

            # Remove the text element from its current parent
            text_element.getparent().remove(text_element)

            # Add to the group
            group_element.append(text_element)

        # Insert the group at the position where the first text element was
        parent.insert(insert_index, group_element)

    @staticmethod
    def get_name():
        return "ids"

    @staticmethod
    def get_description():
        return "Check that all id attributes are unique"


class SVGMatrixChecker(SVGChecker):
    @staticmethod
    def get_name():
        return "matrix"

    @staticmethod
    def get_description():
        return "Checks for malformed matrix transformations in SVG files"

    def check(self):
        elements = self.svg_doc.xpath("//*[@transform]")

        # SVG standard allows numbers with optional leading dot (.5),
        # but requires decimal point to be followed by digit if present
        # See: https://www.w3.org/TR/SVGTiny12/types.html#DataTypeNumber
        float_regex = re.compile(r'^-?(\d+|\d*\.\d+)([eE][-+]?\d+)?$')

        for element in elements:
            transform = element.get("transform")
            if "matrix" in transform:
                try:
                    # Extract values between parentheses
                    matrix_values = transform.split("(")[1].split(")")[0]
                    values = re.split(r'[,\s]+', matrix_values.strip())

                    # Matrix should have exactly 6 values
                    if len(values) != 6:
                        self.add_error(f"Invalid matrix transform (wrong number of values) in element {element.get('id')}: {transform}", node=element)
                        continue

                    # Check for empty values and validate float format
                    if any(not v or not float_regex.match(v) for v in values):
                        self.add_error(f"Invalid matrix transform (invalid value) in element {element.get('id')}: {transform}", node=element)
                        continue

                except IndexError:
                    self.add_error(f"Malformed matrix transform in element {element.get('id')}: {transform}", node=element)

        return self.get_result()


class SVGLayerNestingChecker(SVGChecker):
    def check(self):
        root_element = self.svg_doc.getroot()
        svg_path = self.svg_doc.docinfo.URL

        # Layer groups that shouldn't be nested in certain other layers
        invalid_nesting = {
            'breadboard': ['schematic', 'silkscreen', 'silkscreen0', 'copper0', 'copper1'],
            'schematic': ['breadboard', 'silkscreen', 'silkscreen0', 'copper0', 'copper1'],
            'icon': ['silkscreen', 'silkscreen0', 'copper0', 'copper1', 'breadboard', 'schematic'],
            'silkscreen': ['breadboard', 'schematic', 'copper0', 'copper1'],
            'silkscreen0': ['breadboard', 'schematic', 'copper0', 'copper1'],
            'copper0': ['breadboard', 'schematic', 'silkscreen', 'silkscreen0'],
            'copper1': ['breadboard', 'schematic', 'silkscreen', 'silkscreen0'],
        }

        # Check each main layer group
        for parent_layer, invalid_children in invalid_nesting.items():
            parent_groups = root_element.xpath(f"//*[@id='{parent_layer}']")
            for parent_group in parent_groups:
                # Check for invalid child layers
                for invalid_child in invalid_children:
                    child_elements = parent_group.xpath(f".//*[@id='{invalid_child}']")
                    for element in child_elements:
                        self.add_error(f"Found '{invalid_child}' layer nested inside '{parent_layer}' group, which is invalid. File: {svg_path}", node=element)

        return self.get_result()

    @staticmethod
    def get_name():
        return "layer_nesting"

    @staticmethod
    def get_description():
        return "Check that layer groups are not incorrectly nested (e.g. silkscreen within breadboard)"


class SVGGornChecker(SVGChecker):
    """Check for gorn attributes in SVG files"""
    
    def check(self):
        """Check for gorn attributes in the SVG document"""
        self.errors = 0
        self.warnings = 0
        
        # Search for all elements with gorn attributes
        gorn_elements = self.svg_doc.xpath("//*[@gorn]")
        
        for element in gorn_elements:
            gorn_value = element.get("gorn")
            self.add_error(f"Found gorn attribute with value '{gorn_value}' on element '{element.tag}'", element)
        
        return self.errors, self.warnings
    
    def fix(self, svg_path):
        """Remove gorn attributes from the SVG file"""
        if self.errors == 0:
            return False
            
        try:
            # Read the file content
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use regex to remove gorn attributes (same pattern as removegorn.py)
            gorn_pattern = r'\s*gorn="[\.\d]*"\s*'
            updated_content, count = re.subn(gorn_pattern, ' ', content, flags=re.MULTILINE)
            
            if count > 0:
                # Write the updated content back
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"Removed {count} gorn attributes from {svg_path}")
                return True
            
        except Exception as e:
            print(f"Error removing gorn attributes from {svg_path}: {e}")
        
        return False
    
    @staticmethod
    def get_name():
        return "svg-gorn"
    
    @staticmethod
    def get_description():
        return "Check for unwanted gorn attributes left by the Fritzing parts editor"