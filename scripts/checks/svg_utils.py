class SVGUtils:
    @staticmethod
    def has_visible_attributes(element):
        stroke = SVGUtils.get_inherited_attribute(element, "stroke")
        fill = SVGUtils.get_inherited_attribute(element, "fill")
        stroke_width = SVGUtils.get_inherited_attribute(element, "stroke-width")
        style = SVGUtils.get_inherited_attribute(element, "style")

        # FIXME: Schematic and PCB view should be stricter, and not allow
        # opacity attributes (other than "1") for connectors.
        workaround_styles = ["fill-opacity", "stroke-opacity", "font-size", "stroke-dasharray"]
        if style:
            style_attrs = style.split(";")
            for attr in style_attrs:
                if attr:
                    key, value = attr.split(":")
                    key = key.strip()
                    value = value.strip()
                    # Check: Avoid mixing CSS styles and SVG attributes.
                    if key == "stroke":
                        if stroke:
                            raise ValueError("Style conflict: Stroke attribute already defined as attribute, do not override with style.")
                        stroke = value
                    elif key == "fill":
                        if fill:
                            raise ValueError("Style conflict: Fill attribute already defined as attribute, do not override with style.")
                        fill = value
                    elif key == "stroke-width":
                        if stroke_width:
                            raise ValueError("Style conflict: Stroke-width attribute already defined as attribute, do not override with style.")
                        stroke_width = value
                    elif key not in workaround_styles:
                        raise ValueError(f"Unknown style attribute: {key}")

        if fill and fill != "none":
            return True
        if stroke and stroke != "none" and stroke_width and stroke_width != "0":
            return True

        return False

    @staticmethod
    def get_inherited_attribute(element, attribute_name):
        while element is not None:
            if element.get(attribute_name):
                return element.get(attribute_name)
            element = element.getparent()
        return None


    @staticmethod
    def has_valid_stroke(element):
        stroke = SVGUtils.get_inherited_attribute(element, "stroke")
        stroke_width = SVGUtils.get_inherited_attribute(element, "stroke-width")
        style = SVGUtils.get_inherited_attribute(element, "style")

        if style:
            style_attrs = style.split(";")
            for attr in style_attrs:
                if attr:
                    key, value = attr.split(":")
                    key = key.strip()
                    value = value.strip()
                    if key == "stroke":
                        if stroke:
                            raise ValueError("Style conflict: Stroke attribute already defined as attribute, do not override with style.")
                        stroke = value
                    elif key == "stroke-width":
                        if stroke_width:
                            raise ValueError("Style conflict: Stroke-width attribute already defined as attribute, do not override with style.")
                        stroke_width = value

        if stroke_width and stroke_width != "0":
            if not stroke or stroke == "none":
                return False
        return True

    @staticmethod
    def has_visible_attributes_recursive(element):
        if element.tag.endswith('g'):  # Group element
            for child in element.iterchildren():
                if SVGUtils.has_visible_attributes_recursive(child):
                    return True
            return False
        else:
            return SVGUtils.has_visible_attributes(element)

    # @staticmethod
    # def lazy_load_svg(svg_path):
    #     if svg_path and os.path.exists(svg_path):
    #         try:
    #             return etree.parse(svg_path)
    #         except (FileNotFoundError, etree.XMLSyntaxError) as err:
    #             print(f"Error loading SVG file: {svg_path}")
    #             print(str(err))
    #     return None