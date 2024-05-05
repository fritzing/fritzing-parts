import os

class FZPUtils:
    @staticmethod
    def get_svg_path(fzp_path, image):
        dir_path = os.path.dirname(fzp_path)
        up_one_level = os.path.dirname(dir_path)
        return os.path.join(up_one_level, 'svg', 'core', image)

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
