# Filename: svg_checkers.py
from lxml import etree
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