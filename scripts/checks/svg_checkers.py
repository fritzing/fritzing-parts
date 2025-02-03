# Filename: svg_checkers.py
from lxml import etree
import re
import os
from svg_utils import SVGUtils

class SVGChecker:
    def __init__(self, svg_doc, layer_ids):
        self.svg_doc = svg_doc
        self.layer_ids =  layer_ids

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
            print(f"No font size found for element [{content}]")
            return 1
        if not re.match(r"^\d+(\.\d+)?$", font_size):
            content = self.getChildXML(element)
            print(f"Invalid font size {font_size} unit in element: [{content}]")
            return 1
        return 0
    def check(self):
        errors = 0
        text_elements = self.svg_doc.xpath("//*[local-name()='text' or local-name()='tspan']")
        for element in text_elements:
            errors += self.check_font_size(element)
        return errors


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
        # 'DroidSans-Bold': 'Noto Sans',
        # 'NotoSans-Regular': 'Noto Sans',
        # 'OCRAStd': 'OCR-Fritzing-mono',
        # 'OCRATributeW01 - Regular': 'OCR-Fritzing-mono',
        # 'ocra10': 'OCR-Fritzing-mono',
        # 'OCRATributeW01-Regular': 'OCR-Fritzing-mono',
        # 'OpenSans': 'Noto Sans',
        # 'ArialMT': 'default',
        # 'MyriadPro - Regular': 'default',
        # 'MyriadPro-Regular': 'default',
        # 'HelveticaNeueLTStd-Roman': 'default',
        # 'DroidSans - Bold': 'Noto Sans',
        # 'DroidSans': 'Noto Sans',
        # "Droid": "Noto Sans",
        # 'Droid Sans Mono': 'default',
        # 'DroidSansMono': 'default',
        # 'Arial-BoldMT': 'Noto Sans',
        # 'EurostileLTStd': 'Noto Sans',
    }

    def __init__(self, svg_doc, layer_ids):
        super().__init__(svg_doc, layer_ids)
        self.is_pcb_view = 'copper' in layer_ids or 'silkscreen' in layer_ids
        self.default_font = 'OCR-Fritzing-mono' if self.is_pcb_view else 'Noto Sans'

    def has_inherited_style(self, element):
        """Check if element has an inherited style attribute"""
        return SVGUtils.get_inherited_attribute(element, "style") is not None

    def fix(self):
        """
        Fixes invalid or missing font families in the SVG document.
        Skips elements that have or inherit style attributes.
        Only fixes direct font-family attributes.
        """
        modified = False
        text_elements = self.svg_doc.xpath("//*[local-name()='text' or local-name()='tspan']")

        for element in text_elements:
            # Skip if element has or inherits a style attribute
            if self.has_inherited_style(element):
                print(f"Skipping element with inherited style attribute: [{self.getChildXML(element)}]")
                continue

            font_family = SVGUtils.get_inherited_attribute(element, "font-family")

            if font_family is None:
                # If it's a text element that contains child elements, skip adding default
                if element.tag.endswith("text") and len(element) > 0:
                    print(f"Skipping font addition for element with child elements: [{self.getChildXML(element)}]")
                    continue
                # Otherwise, add missing font-family attribute
                element.set("font-family", self.default_font)
                print(f"Added default font '{self.default_font}' to element: [{self.getChildXML(element)}]")
                modified = True
                continue

            # Remove quotes if present
            font_family = font_family.strip('"\'')

            if font_family not in self.VALID_FONTS:
                # Only replace if the font is in the replacement list
                if font_family in self.FONT_REPLACEMENTS:
                    new_font = self.FONT_REPLACEMENTS[font_family]
                    # Handle special 'default' replacement value
                    if new_font == 'default':
                        new_font = self.default_font

                    element.set("font-family", new_font)
                    content = self.getChildXML(element)
                    print(f"Replaced font '{font_family}' with '{new_font}' in element: [{content}]")
                    modified = True
                # else: keep the unknown font

        if modified:
            try:
                # Get the file path from the SVG document
                svg_path = self.svg_doc.docinfo.URL
                if svg_path:
                    # Create backup
                    backup_path = svg_path + ".bak"
                    if not os.path.exists(backup_path):
                        self.svg_doc.write(backup_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                        print(f"Backup created at '{backup_path}'")

                    # Write modified SVG
                    self.svg_doc.write(svg_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                    print(f"SVG file '{svg_path}' has been updated successfully")
                    return True
            except Exception as e:
                print(f"Failed to write SVG file: {str(e)}")
                return False
        else:
            print("No fonts found to add or replace. No changes made.")
            return False


    def check_font_type(self, element):
        font_family = SVGUtils.get_inherited_attribute(element, "font-family")
        if font_family is None:
            if element.tag.endswith("text"):
                for child in element.iterchildren():
                    if child.tag.endswith("tspan"):
                        return self.check_font_type(child)
            content = self.getChildXML(element)
            print(f"No font family found for element [{content}]")
            return 1

        # Remove quotes if present
        font_family = font_family.strip('"\'')

        if font_family not in self.VALID_FONTS:
            content = self.getChildXML(element)
            print(f"Invalid font family '{font_family}' in element: [{content}]")
            return 1
        return 0

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
        errors = 0
        text_elements = self.svg_doc.xpath("//*[local-name()='text' or local-name()='tspan']")
        for element in text_elements:
            errors += self.check_font_type(element)
        return errors

    @staticmethod
    def get_name():
        return "font_type"

    @staticmethod
    def get_description():
        return "Check that font-family attributes use only allowed fonts (Noto Sans, OCR-Fritzing-mono, DroidSans, OCRA)"


class SVGViewBoxChecker(SVGChecker):
    def check(self):
        errors = 0

        # For icons, we don't really need a viewBox
        if self.layer_ids == ['icon']:
            return errors

        root_element = self.svg_doc.getroot()
        if "viewBox" in root_element.attrib:
            viewbox = root_element.attrib["viewBox"]
            if not re.match(r"^-?\d+(\.\d+)?( -?\d+(\.\d+)?){3}$", viewbox):
                print(f"Invalid viewBox attribute: {viewbox}")
                errors += 1
        else:
            print("Missing viewBox attribute")
            errors += 1
        return errors

    @staticmethod
    def get_name():
        return "viewbox"

    @staticmethod
    def get_description():
        return "Check that the viewBox attribute is valid"


class SVGIdsChecker(SVGChecker):
    def check(self):
        errors = 0
        id_set = set()
        elements_with_id = self.svg_doc.xpath("//*[@id]")
        for element in elements_with_id:
            element_id = element.attrib["id"]
            if element_id in id_set:
                print(f"Duplicate id attribute: {element_id}")
                errors += 1
            else:
                id_set.add(element_id)
        return errors

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
        errors = 0
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
                        print(f"Invalid matrix transform (wrong number of values) in element {element.get('id')}: {transform}")
                        errors += 1
                        continue

                    # Check for empty values and validate float format
                    if any(not v or not float_regex.match(v) for v in values):
                        print(f"Invalid matrix transform (invalid value) in element {element.get('id')}: {transform}")
                        errors += 1
                        continue

                except IndexError:
                    print(f"Malformed matrix transform in element {element.get('id')}: {transform}")
                    errors += 1

        return errors