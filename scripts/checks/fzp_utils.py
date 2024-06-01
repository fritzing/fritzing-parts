import os
import re

class FZPUtils:
    @staticmethod
    def get_svg_path(fzp_path, image, view_name):
        dir_path = os.path.dirname(fzp_path)
        up_one_level = os.path.dirname(dir_path)
        svg_path = os.path.join(up_one_level, 'svg', 'core', image)

        if FZPUtils.is_template(svg_path, view_name):
            return None  # Skip template SVGs

        return svg_path

    @staticmethod
    def is_template(svg_path, view):
        # Extract the filename from the svg_path
        filename = os.path.basename(svg_path)

        # Initialize the flag to False
        starts_with_prefix = False

        if view == 'breadboardView':
            # Check if filename starts with 'generic_ic_' or matches the 'generic_female_pin_header_' pattern
            if filename.startswith('generic_ic_'):
                starts_with_prefix = True
            else:
                # Define regex pattern for 'generic_female_pin_header_' filenames
                pattern = r'^generic_female_pin_header_\d+_100mil_bread\.svg$'
                starts_with_prefix = bool(re.match(pattern, filename))

        elif view == 'iconView':
            # For iconView, the filename should still start with 'generic_ic_'
            starts_with_prefix = filename.startswith('generic_ic_')

        elif view == 'schematicView':
            # For schematicView, the filename should start with 'generic_'
            starts_with_prefix = filename.startswith('generic_')

        elif view == 'pcbView':
            # For pcbView, check if the filename matches the 'dip_' or 'jumper_' pattern
            dip_pattern = r'^dip_\d+_\d+mil_pcb\.svg$'
            jumper_pattern = r'^jumper_\d+_\d+mil_pcb\.svg$'
            starts_with_prefix = bool(re.match(dip_pattern, filename) or re.match(jumper_pattern, filename))

        # Define valid views
        valid_views = ['breadboardView', 'iconView', 'schematicView', 'pcbView']

        # Check if the view is valid and if the filename starts with the correct prefix or matches the pattern
        valid_view = view in valid_views
        return starts_with_prefix and valid_view

    @staticmethod
    def get_svg_path_from_view(fzp_doc, fzp_path, view_name, layer=None):
        views_section = fzp_doc.xpath("//views")[0]
        for view in views_section:
            if view.tag == view_name:
                layers = view.xpath("layers")
                if layers:
                    if layer:
                        layer_elements = layers[0].xpath("layer")
                        for layer_element in layer_elements:
                            if layer_element.attrib.get("layerId") == layer:
                                image = layers[0].attrib.get("image")
                                if image:
                                    return FZPUtils.get_svg_path(fzp_path, image, view.tag)
                    else:
                        image = layers[0].attrib.get("image")
                        if image:
                            return FZPUtils.get_svg_path(fzp_path, image, view.tag)
        return None


    @staticmethod
    def is_hybrid_or_unknown_layer(p_element):
        layer = p_element.attrib.get("layer")
        is_hybrid = p_element.attrib.get("hybrid") == "yes"
        if not is_hybrid and layer == "unknown":
            print(f"Unknown layer for regular connector in {p_element}.")
        return layer == "unknown" or is_hybrid