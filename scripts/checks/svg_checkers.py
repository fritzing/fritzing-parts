from xml.dom import minidom
import re

class SVGChecker:
    def __init__(self, svg_doc):
        self.svg_doc = svg_doc

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
            font_size = element.getAttribute("font-size")
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


class SVGInvisibleConnectorsChecker(SVGChecker):
    def check(self):
        errors = 0
        connectors = self.svg_doc.getElementsByTagName("*")
        for element in connectors:
            if "connector" not in element.getAttribute("id"):
                continue
            if "terminal" in element.getAttribute("id"):
                continue

            has_visible_child = False
            for child in element.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    fill = child.getAttribute("fill")
                    if fill and fill != "none":
                        has_visible_child = True
                        break

            if has_visible_child:
                continue

            stroke = element.getAttribute("stroke")
            fill = element.getAttribute("fill")
            stroke_width = element.getAttribute("stroke-width")

            if not stroke:
                style = element.getAttribute("style")
                if style:
                    style = style.replace(";", ":")
                    styles = style.split(":")
                    for index, name in enumerate(styles):
                        if name == "stroke":
                            stroke = styles[index + 1]
                        elif name == "stroke-width":
                            stroke_width = styles[index + 1]
                        elif name == "fill":
                            fill = styles[index + 1]

            if (len(fill) > 0 and fill != "none") or (len(stroke) > 0 and stroke != "none"):
                continue

            if len(stroke_width) > 0 and stroke_width != "0":
                if stroke == "none":
                    print(f"Invisible connector: {element.getAttribute('id')}")
                    print("  stroke-width is > 0 but stroke is 'none'")
                    errors += 1
                continue

            print(f"Invisible connector: {element.getAttribute('id')}")
            errors += 1

        return errors

    @staticmethod
    def get_name():
        return "invisible_connectors"

    @staticmethod
    def get_description():
        return "Check for invisible connectors in the SVG file"
