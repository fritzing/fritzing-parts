# Filename: svg_checkers.py
from lxml import etree
import re
import os
import logging
from .svg_utils import SVGUtils
from .fzp_checkers import ValidationIssue, FixResult

class SVGChecker:
    def __init__(self, svg_doc, layer_ids):
        self.svg_doc = svg_doc
        self.layer_ids = layer_ids
        self.errors = 0
        self.warnings = 0
        self.issues = []
        self.fixes = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_error(self, message, node=None):
        issue = ValidationIssue(message, severity='error', node=node)
        self.issues.append(issue)
        self.logger.debug(f"Error: {message}")
        self.errors += 1

    def add_warning(self, message, node=None):
        issue = ValidationIssue(message, severity='warning', node=node)
        self.issues.append(issue)
        self.logger.debug(f"Warning: {message}")
        self.warnings += 1

    def add_fix(self, message, node=None, line_number=None):
        fix = FixResult(message, node=node, line_number=line_number)
        self.fixes.append(fix)
        self.logger.debug(f"Fixed: {message}")

    def get_result(self):
        return self.errors, self.warnings
    
    def get_fixes_count(self):
        return len(self.fixes)

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

    def fix(self, filename):
        """Strip unit suffixes (px, mm, pt, etc.) from font-size values.

        Handles both XML attributes (font-size="5px") and CSS style
        properties (style="font-size:5px;...").
        """
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        units = r'(?:px|mm|pt|in|cm|em|ex|rem|%)'

        # Fix font-size XML attributes: font-size="5px" -> font-size="5"
        attr_pattern = r'(font-size\s*=\s*(["\']))(\d+(?:\.\d+)?)\s*' + units + r'(\2)'

        def replace_attr(match):
            prefix = match.group(1)    # font-size="  (including quote)
            number = match.group(3)
            closing = match.group(4)   # closing quote
            old_val = match.group(0)
            self.add_fix(f"Removed unit from font-size attribute: {old_val} -> {prefix}{number}{closing}")
            return f'{prefix}{number}{closing}'

        content = re.sub(attr_pattern, replace_attr, content)

        # Fix font-size inside style attributes: font-size:5px -> font-size:5
        style_pattern = r'(font-size\s*:\s*)(\d+(?:\.\d+)?)\s*' + units + r'(\s*[;"\'])'

        def replace_style(match):
            prefix = match.group(1)    # font-size:
            number = match.group(2)
            suffix = match.group(3)    # ; or closing quote
            old_val = match.group(0)
            self.add_fix(f"Removed unit from font-size in style: {old_val} -> {prefix}{number}{suffix}")
            return f'{prefix}{number}{suffix}'

        content = re.sub(style_pattern, replace_style, content)

        if content != original_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

        return self.fixes

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
        "'DroidSans'": 'Noto Sans',
        'DroidSans': 'Noto Sans',
        "'Droid Sans'": 'Noto Sans',
        "Droid": "Noto Sans",
        'Droid Sans Mono': 'default',
        'DroidSansMono': 'default',
        "'DroidSans, 'Droid Sans'": 'Noto Sans',
        "DroidSans, 'Droid Sans'": 'Noto Sans',
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

        # Read the original file
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()

        modified = False
        original_content = content

        # Pattern to match font-family with any quote style, including nested quotes
        # Handles cases like font-family="'DroidSans, 'Droid Sans'"
        pattern = r'font-family\s*=\s*(["\'])([^\1]*?)\1'

        def replace_font(match):
            nonlocal modified
            quote_char = match.group(1)  # The quote character used
            font = match.group(2)        # The font name content
            if font in self.FONT_REPLACEMENTS:
                new_font = self.FONT_REPLACEMENTS[font]
                if new_font == 'default':
                    new_font = self.default_font
                modified = True
                self.add_fix(f"Replaced font '{font}' with '{new_font}' in {filename}")
                # Always use double quotes for consistency
                return f'font-family="{new_font}"'
            return match.group(0)

        # Debug: Show all matches found
        matches = re.findall(pattern, content)
        self.logger.debug(f"Font-family matches found: {matches}")
        
        # Make replacements
        content = re.sub(pattern, replace_font, content)

        if modified:
            # Create backup if it doesn't exist
            backup_path = filename + ".bak"
            if not os.path.exists(backup_path):
                with open(backup_path, 'w', encoding='utf-8') as file:
                    file.write(original_content)
                self.logger.debug(f"Backup created at '{backup_path}'")

            # Write modified content only if changes were made
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(content)
            self.logger.debug(f"SVG file '{filename}' has been updated successfully")
            return self.fixes
        else:
            self.logger.debug("No fonts found to replace. No changes made.")
            return self.fixes



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
        
        # First pass: collect all occurrences and check for empty IDs
        for element in elements_with_id:
            element_id = element.attrib["id"]
            
            # Check for empty or whitespace-only IDs
            if not element_id or element_id.isspace():
                self.add_warning(f"Element has empty or whitespace-only id attribute - should be removed", node=element)
                continue
                
            if element_id not in id_occurrences:
                id_occurrences[element_id] = []
            id_occurrences[element_id].append(element)
        
        # Second pass: report duplicates with enumeration
        for element_id, elements in id_occurrences.items():
            if len(elements) > 1:
                for i, element in enumerate(elements, 1):
                    self.add_error(f"Duplicate id attribute: {element_id} (occurrence {i} of {len(elements)})", node=element)
        
        return self.get_result()

    def fix(self, filename):
        """Fix SVG ID issues: 1) Remove empty IDs, 2) Fix duplicate 'label' IDs by combining consecutive text elements"""
        import re

        # Use the provided filename
        svg_path = filename
        if not svg_path:
            self.logger.debug("Cannot fix SVG IDs - file path not found")
            return False

        fixes_applied = False
        
        # Read the original file for string-based operations
        with open(svg_path, 'r', encoding='utf-8') as file:
            content = file.read()
        original_content = content

        # First: Remove empty or whitespace-only IDs using regex
        empty_id_pattern = r'\s+id\s*=\s*["\']["\']'  # matches id="" or id=''
        whitespace_id_pattern = r'\s+id\s*=\s*["\'][\s]*["\']'  # matches id=" " etc
        
        empty_matches = len(re.findall(empty_id_pattern, content))
        whitespace_matches = len(re.findall(whitespace_id_pattern, content))
        
        if empty_matches > 0 or whitespace_matches > 0:
            content = re.sub(empty_id_pattern, '', content)
            content = re.sub(whitespace_id_pattern, '', content)
            total_removed = empty_matches + whitespace_matches
            self.add_fix(f"Removed {total_removed} empty/whitespace id attributes in {svg_path}")
            fixes_applied = True

        # Second: Handle duplicate label IDs
        label_elements = self.svg_doc.xpath("//*[local-name()='text' and @id='label']")

        if len(label_elements) <= 1:
            if not fixes_applied:
                self.logger.debug(f"No duplicate text elements with id='label' to fix in {svg_path}")
            return self.fixes

        self.logger.debug(f"Found {len(label_elements)} text elements with id='label' in {svg_path}")

        # Group consecutive elements
        consecutive_groups = self._find_consecutive_groups(label_elements)

        # Check if there are actually groups to fix
        groups_to_fix = [group for group in consecutive_groups if len(group) > 1]
        
        # Count total elements that could be fixed vs those in consecutive groups
        total_fixable_elements = sum(len(group) for group in groups_to_fix)
        
        if not groups_to_fix:
            # We have duplicates but no consecutive groups - this can't be auto-fixed
            self.add_error(f"Found {len(label_elements)} duplicate label IDs that are not consecutive and cannot be automatically fixed in {svg_path}")
            return self.fixes
        elif total_fixable_elements < len(label_elements):
            # We have some consecutive groups but also some non-consecutive duplicates
            non_consecutive_count = len(label_elements) - total_fixable_elements
            self.add_error(f"Found {non_consecutive_count} non-consecutive duplicate label IDs that cannot be automatically fixed in {svg_path}")

        self.logger.debug(f"Found {len(groups_to_fix)} groups of consecutive label elements to fix")

        # Process each group (in reverse order to maintain positions)
        for i, group in enumerate(reversed(groups_to_fix)):
            self.logger.debug(f"Creating group {i+1} with {len(group)} text elements")
            content = self._replace_label_group_in_content(content, group)
            self.add_fix(f"Successfully fixed {len(groups_to_fix)} groups of duplicate label IDs in {svg_path}")
            fixes_applied = True

        # Write the modified content back if any fixes were applied
        if fixes_applied:
            with open(svg_path, 'w', encoding='utf-8') as file:
                file.write(content)

        return self.fixes

    def _replace_label_group_in_content(self, content, text_elements):
        """Replace consecutive text elements with id='label' with a single text element containing tspan children"""
        import re

        # Use a simpler approach - find all text elements with id="label" in the content
        # and match them by position and content
        label_pattern = r'<text[^>]*id="label"[^>]*>.*?</text>'
        label_matches = []

        for match in re.finditer(label_pattern, content, re.DOTALL):
            # Extract the full element text
            element_text = match.group(0)

            # Check if this matches any of our target elements by x, y, and text content
            for elem in text_elements:
                x_val = elem.get('x', '')
                y_val = elem.get('y', '')
                text_content = elem.text or ""

                # Check if this element matches by looking for x, y, and text content
                if (f'x="{x_val}"' in element_text and
                    f'y="{y_val}"' in element_text and
                    text_content in element_text):
                    label_matches.append((match.start(), match.end(), element_text))
                    break

        found_elements = label_matches

        if len(found_elements) < 2:
            return content  # Not enough elements to group

        # Sort by position in file
        found_elements.sort()

        # Get the original indentation from the first element
        first_start = found_elements[0][0]
        line_start = content.rfind('\n', 0, first_start) + 1
        original_indent = content[line_start:first_start]

        # Create the text element with tspan children replacement with proper indentation
        # Extract attributes from the first text element
        first_element = found_elements[0][2]

        # Extract common attributes from first element (x, y, fill, font-family, font-size, text-anchor)
        import re
        x_match = re.search(r'\bx="([^"]*)"', first_element)
        y_match = re.search(r'\by="([^"]*)"', first_element)
        fill_match = re.search(r'\bfill="([^"]*)"', first_element)
        font_family_match = re.search(r'\bfont-family="([^"]*)"', first_element)
        font_size_match = re.search(r'\bfont-size="([^"]*)"', first_element)
        text_anchor_match = re.search(r'\btext-anchor="([^"]*)"', first_element)

        x_val = x_match.group(1) if x_match else "0"
        y_val = y_match.group(1) if y_match else "0"
        fill_val = fill_match.group(1) if fill_match else "#000000"
        font_family_val = font_family_match.group(1) if font_family_match else "Noto Sans"
        font_size_val = font_size_match.group(1) if font_size_match else "3.5"
        text_anchor_val = text_anchor_match.group(1) if text_anchor_match else "middle"

        # Create text element with tspan children
        group_content = original_indent + f'<text id="label" x="{x_val}" y="{y_val}" fill="{fill_val}" font-family="{font_family_val}" font-size="{font_size_val}" text-anchor="{text_anchor_val}">\n'

        for i, (_, _, element_str) in enumerate(found_elements):
            # Extract text content from each element
            text_match = re.search(r'<text[^>]*>([^<]*)</text>', element_str)
            text_content = text_match.group(1) if text_match else ""
            # Extract y position from this specific element
            y_match = re.search(r'\by="([^"]*)"', element_str)
            element_y = y_match.group(1) if y_match else y_val

            # Create tspan with x and y attributes, no dx/dy as requested
            group_content += original_indent + f'   <tspan x="{x_val}" y="{element_y}">{text_content}</tspan>\n'

        group_content += original_indent + '</text>'

        # Replace all the individual elements with the group
        # Remove from end to start to preserve positions
        for start, end, _ in reversed(found_elements):
            if start == found_elements[0][0]:  # First element - replace with group
                # Replace including the original indentation (which is already in group_content)
                line_start = content.rfind('\n', 0, start) + 1
                content = content[:line_start] + group_content + content[end:]
            else:  # Other elements - remove including their line and indentation
                # Find the start of the line (including indentation)
                line_start = content.rfind('\n', 0, start) + 1
                # Check if there's a newline after the element to remove it too
                end_pos = end
                if end_pos < len(content) and content[end_pos] == '\n':
                    end_pos += 1
                content = content[:line_start] + content[end_pos:]

        return content

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
            'breadboard': ['schematic', 'icon', 'silkscreen', 'silkscreen0', 'copper0', 'copper1'],
            'schematic': ['breadboard', 'icon', 'silkscreen', 'silkscreen0', 'copper0', 'copper1'],
            'icon': ['silkscreen', 'silkscreen0', 'copper0', 'copper1', 'breadboard', 'schematic'],
            'silkscreen': ['breadboard', 'schematic', 'icon', 'copper0', 'copper1'],
            'silkscreen0': ['breadboard', 'schematic', 'icon', 'copper0', 'copper1'],
            'copper0': ['breadboard', 'schematic', 'icon', 'silkscreen', 'silkscreen0'],
            'copper1': ['breadboard', 'schematic', 'icon', 'silkscreen', 'silkscreen0'],
        }

        # Check each main layer group
        for parent_layer, invalid_children in invalid_nesting.items():
            parent_groups = root_element.xpath(f"//*[@id='{parent_layer}']")
            for parent_group in parent_groups:
                # Check for invalid child layers
                for invalid_child in invalid_children:
                    child_elements = parent_group.xpath(f".//*[@id='{invalid_child}']")
                    for element in child_elements:
                        # icon inside breadboard (or vice versa) is unsupported but not fatal
                        pair = {parent_layer, invalid_child}
                        if pair == {'breadboard', 'icon'}:
                            self.add_warning(f"Found '{invalid_child}' layer nested inside '{parent_layer}' group, which is unsupported. File: {svg_path}", node=element)
                        else:
                            self.add_error(f"Found '{invalid_child}' layer nested inside '{parent_layer}' group, which is invalid. File: {svg_path}", node=element)

        return self.get_result()

    @staticmethod
    def get_name():
        return "layer_nesting"

    @staticmethod
    def get_description():
        return "Check that layer groups are not incorrectly nested (e.g. silkscreen within breadboard)"


class SVGCopperLayerContentChecker(SVGChecker):
    """
    Validates that copper layer groups (copper0, copper1) only contain
    copper-colored elements and no non-copper colors.

    This prevents the common mistake of using silkscreen colors (white, gray)
    or other non-copper colors within copper layer groups, which causes
    rendering issues.
    """

    # RGB threshold for color similarity (Euclidean distance)
    # Set high enough to catch all copperish/golden/orange colors
    # but low enough to reject silkscreen colors (white ~227, black ~311)
    RGB_DISTANCE_THRESHOLD = 75.0
    STANDARD_COPPER_RGB = (247, 189, 19)  # #f7bd13

    def check(self):
        """Check copper0 and copper1 layers for invalid content"""
        # Skip if not a PCB view
        if 'copper0' not in self.layer_ids and 'copper1' not in self.layer_ids:
            return self.get_result()

        # Check both copper layers
        for layer in ['copper0', 'copper1']:
            layer_groups = self.svg_doc.xpath(f"//*[@id='{layer}']")
            for group in layer_groups:
                self._check_copper_layer_colors(group, layer)

        return self.get_result()

    def _check_copper_layer_colors(self, layer_group, layer_id):
        """Check colors of all elements within a copper layer group"""
        # Get all descendant elements
        descendants = layer_group.xpath(".//*")

        for element in descendants:
            # Skip copper layer groups themselves (copper0 in copper1 is valid)
            if element.get('id') in ['copper0', 'copper1']:
                continue

            self._check_element_colors(element, layer_id)

    def _check_element_colors(self, element, layer_id):
        """Check fill and stroke colors of an element"""
        # Get attributes (may be overridden by style)
        fill = SVGUtils.get_inherited_attribute(element, 'fill')
        stroke = SVGUtils.get_inherited_attribute(element, 'stroke')
        stroke_width = SVGUtils.get_inherited_attribute(element, 'stroke-width')
        style = SVGUtils.get_inherited_attribute(element, 'style')

        # Parse style attribute if present (style overrides attributes)
        if style:
            style_attrs = style.split(";")
            for attr in style_attrs:
                if attr:
                    parts = attr.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key == "fill":
                            fill = value
                        elif key == "stroke":
                            stroke = value
                        elif key == "stroke-width":
                            stroke_width = value

        # Check fill color
        if fill and fill.lower() != 'none':
            result = self._is_valid_copper_color(fill, element, layer_id, 'fill')
            if not result:
                self._report_invalid_color(element, layer_id, fill, 'fill')

        # Check stroke color (only if stroke is visible)
        if stroke and stroke.lower() != 'none':
            # Only check stroke if it's visible (has non-zero width)
            if stroke_width and stroke_width != '0':
                result = self._is_valid_copper_color(stroke, element, layer_id, 'stroke')
                if not result:
                    self._report_invalid_color(element, layer_id, stroke, 'stroke')

    def _is_valid_copper_color(self, color, element, layer_id, attr_type):
        """Check if color is a valid copper color

        Only #f7bd13 passes without warning.
        Near colors (within threshold) generate a warning.
        Far colors generate an error (by returning False).
        """
        if not color:
            return True

        # Convert color to RGB for comparison
        try:
            rgb = self._color_to_rgb(color)
            if not rgb:
                return False

            # Check if exact match with standard copper color
            if rgb == self.STANDARD_COPPER_RGB:
                return True

            # Check RGB distance from standard copper color
            distance = self._rgb_distance(rgb, self.STANDARD_COPPER_RGB)

            if distance <= self.RGB_DISTANCE_THRESHOLD:
                # Near color - issue warning but don't fail
                element_id = element.get('id', '(no id)')
                element_tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                self.add_warning(
                    f"Non-standard copper color '{color}' found in copper layer '{layer_id}'. "
                    f"Expected exact color (#f7bd13). "
                    f"Element: {element_tag} with id='{element_id}' ({attr_type} attribute)",
                    node=element
                )
                return True

            # Far color - will trigger error
            return False
        except:
            pass

        return False

    def _color_to_rgb(self, color):
        """Convert color (hex or rgb notation) to RGB tuple

        Handles normalization (lowercase, whitespace removal) internally.
        """
        # Normalize color (lowercase, remove whitespace)
        color = color.strip().lower()

        # Handle rgb(r, g, b) notation
        if color.startswith('rgb(') and color.endswith(')'):
            try:
                rgb_values = color[4:-1].split(',')
                return tuple(int(v.strip()) for v in rgb_values)
            except (ValueError, IndexError):
                return None

        # Handle hex notation
        hex_color = color.lstrip('#')
        if len(hex_color) != 6:
            return None
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            return None

    def _rgb_distance(self, rgb1, rgb2):
        """Calculate Euclidean distance between two RGB colors"""
        return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5

    def _report_invalid_color(self, element, layer_id, color, attr_type):
        """Report an invalid color error"""
        element_id = element.get('id', '(no id)')
        element_tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        self.add_error(
            f"Invalid color '{color}' found in copper layer '{layer_id}'. "
            f"Expected copper color (#f7bd13). "
            f"Element: {element_tag} with id='{element_id}' ({attr_type} attribute)",
            node=element
        )

    @staticmethod
    def get_name():
        return "copper_layer_content"

    @staticmethod
    def get_description():
        return "Check that copper layers only contain copper-colored elements (no silkscreen or other layer content)"


class SVGNoLayerChecker(SVGChecker):
    """Check that SVG child elements are inside proper Fritzing layer groups."""

    VALID_LAYERS = [
        "icon", "breadboardbreadboard", "breadboard", "breadboardWire",
        "breadboardLabel", "breadboardNote", "breadboardRuler",
        "schematic", "schematicWire", "schematicTrace", "schematicLabel",
        "schematicRuler", "board", "ratsnest", "silkscreen",
        "silkscreenLabel", "groundplane", "copper0", "copper0trace",
        "groundplane1", "copper1", "copper1trace", "silkscreen0",
        "silkscreen0Label", "soldermask", "outline", "keepout",
        "partimage", "pcbNote", "pcbRuler"
    ]

    SKIP_LOCAL_TAGS = {"metadata", "title", "desc", "defs", "namedview"}

    def _check_element(self, element):
        """Walk direct children of element, checking for valid layer groups."""
        for child in element:
            tag = etree.QName(child.tag).localname if '}' in child.tag else child.tag

            if tag in self.SKIP_LOCAL_TAGS:
                continue

            child_id = child.get("id", "")
            if child_id in self.VALID_LAYERS:
                continue

            if tag == "g":
                result = self._check_element(child)
                if result:
                    return result
                continue

            return tag

        return None

    def check(self):
        root = self.svg_doc.getroot()

        # Check that root <svg> doesn't have a layer ID (Fritzing bug)
        root_id = root.get("id", "")
        if root_id in self.VALID_LAYERS:
            self.add_error(
                f"Root <svg> element contains layer id '{root_id}' — "
                f"Fritzing has problems with layer ids in the root element",
                node=root
            )
            return self.get_result()

        bad_tag = self._check_element(root)
        if bad_tag:
            self.add_error(
                f"Child element '{bad_tag}' is not inside a valid Fritzing layer group "
                f"(expected a <g> with id matching a known layer)",
                node=root
            )

        return self.get_result()

    @staticmethod
    def get_name():
        return "no_layer"

    @staticmethod
    def get_description():
        return "Check that SVG child elements are inside proper Fritzing layer groups (e.g. <g id='breadboard'>)"


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
            self.logger.debug(f"No gorns to fix for {svg_path}")
            return self.fixes
        else:
            self.logger.debug(f"{self.errors} gorns to fix for {svg_path}")

        # Read the file content
        with open(svg_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all gorn attributes with their details before removing them
        gorn_pattern = r'\s*gorn="([\.\d]*)"\s*'
        gorn_matches = []

        # Split content into lines for line number tracking
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(gorn_pattern, line):
                gorn_value = match.group(1)
                gorn_matches.append({
                    'value': gorn_value,
                    'line_number': line_num,
                    'full_match': match.group(0).strip()
                })

        # Remove gorn attributes using the same pattern
        updated_content, count = re.subn(gorn_pattern, ' ', content, flags=re.MULTILINE)

        if count > 0:
            # Write the updated content back
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            # Add one detailed fix entry per gorn attribute removed
            for gorn_info in gorn_matches:
                self.add_fix(
                    f"Removed gorn attribute '{gorn_info['full_match']}' (value: {gorn_info['value']}) from line {gorn_info['line_number']} in {svg_path}",
                    line_number=gorn_info['line_number']
                )

        return self.fixes
    
    @staticmethod
    def get_name():
        return "svg-gorn"
    
    @staticmethod
    def get_description():
        return "Check for unwanted gorn attributes left by the Fritzing parts editor"
