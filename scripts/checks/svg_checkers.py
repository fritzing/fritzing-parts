from xml.dom import minidom
import re
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
    def check(self):
        errors = 0
        text_elements = self.svg_doc.getElementsByTagName("text")
        for element in text_elements:
            font_size = SVGUtils.get_inherited_attribute(element, "font-size")
            if not re.match(r"^\d+(\.\d+)?$", font_size):
                print(f"Invalid font size in <text> element: {font_size}")
                errors += 1
        return errors

    @staticmethod
    def get_name():
        return "font_size"

    @staticmethod
    def get_description():
        return "Check that the font-size attribute of each text element is a valid number"


class SVGViewBoxChecker(SVGChecker):
    def check(self):
        errors = 0

        # For icons, we don't really need a viewBox
        if self.layer_ids == ['icon']:
            return errors

        root_element = self.svg_doc.documentElement
        if root_element.hasAttribute("viewBox"):
            viewbox = root_element.getAttribute("viewBox")
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
        elements_with_id = self.svg_doc.getElementsByTagName("*")
        for element in elements_with_id:
            if element.hasAttribute("id"):
                element_id = element.getAttribute("id")
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


