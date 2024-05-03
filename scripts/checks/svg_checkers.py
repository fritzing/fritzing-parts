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
        text_elements = self.svg_doc.getElementsByTagName("text")
        for element in text_elements:
            font_size = element.getAttribute("font-size")
            if not re.match(r"^\d+(\.\d+)?$", font_size):
                print(f"Invalid font size in <text> element: {font_size}")

    @staticmethod
    def get_name():
        return "font_size"

    @staticmethod
    def get_description():
        return "Check that the font-size attribute of each text element is a valid number"


class SVGViewBoxChecker(SVGChecker):
    def check(self):
        root_element = self.svg_doc.documentElement
        if root_element.hasAttribute("viewBox"):
            viewbox = root_element.getAttribute("viewBox")
            if not re.match(r"^-?\d+(\.\d+)?( -?\d+(\.\d+)?){3}$", viewbox):
                print(f"Invalid viewBox attribute: {viewbox}")
        else:
            print("Missing viewBox attribute")

    @staticmethod
    def get_name():
        return "viewbox"

    @staticmethod
    def get_description():
        return "Check that the viewBox attribute is valid"


class SVGIdsChecker(SVGChecker):
    def check(self):
        id_set = set()
        elements_with_id = self.svg_doc.getElementsByTagName("*")
        for element in elements_with_id:
            if element.hasAttribute("id"):
                element_id = element.getAttribute("id")
                if element_id in id_set:
                    print(f"Duplicate id attribute: {element_id}")
                else:
                    id_set.add(element_id)

    @staticmethod
    def get_name():
        return "ids"

    @staticmethod
    def get_description():
        return "Check that all id attributes are unique"

class SVGInvisibleConnectorsChecker(SVGChecker):
    def check(self):
        connectors = self.svg_doc.getElementsByTagName("*")
        for element in connectors:
            if "connector" not in element.getAttribute("id"):
                continue
            if "terminal" in element.getAttribute("id"):
                continue

            hasVisibleChild = False
            for child in element.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    fill = child.getAttribute("fill")
                    if fill and fill != "none":
                        hasVisibleChild = True
                        break

            if hasVisibleChild:
                continue

            stroke = element.getAttribute("stroke")
            fill = element.getAttribute("fill")
            strokewidth = element.getAttribute("stroke-width")

            if not stroke:
                style = element.getAttribute("style")
                if style:
                    style = style.replace(";", ":")
                    styles = style.split(":")
                    for index, name in enumerate(styles):
                        if name == "stroke":
                            stroke = styles[index + 1]
                        elif name == "stroke-width":
                            strokewidth = styles[index + 1]
                        elif name == "fill":
                            fill = styles[index + 1]

            if (len(fill) > 0 and fill != "none") or (len(stroke) > 0 and stroke != "none"):
                continue

            if len(strokewidth) > 0 and strokewidth != "0":
                if stroke == "none":
                    print("invisible connector", svgFilename, element.getAttribute("id"))
                    print("  strokewidth is > 0 but stroke is 'none'")
                continue

            print("invisible connector", svgFilename, element.getAttribute("id"))

            print(f"Invisible connector found: {element.getAttribute('id')}")

    @staticmethod
    def get_name():
        return "invisible_connectors"

    @staticmethod
    def get_description():
        return "Check for invisible connectors in the SVG file"