import os
import re
import zipfile
import tempfile
import shutil

class FZPUtils:
    @staticmethod
    def get_svg_path(fzp_path, image, view_name):
        dir_path = os.path.dirname(fzp_path)
        
        # For fzpz files, the image path might include subdirectories like "svg/core/breadboard/file.svg"
        # but the actual file is just "file.svg" in the same directory
        image_filename = os.path.basename(image)
        
        # Check if this is an extracted fzpz structure (SVGs in same directory as FZP)
        if FZPUtils.is_fzpz_structure(fzp_path, image_filename):
            svg_path = os.path.join(dir_path, image_filename)
        else:
            # Standard fritzing-parts structure
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
    def is_fzpz_structure(fzp_path, image):
        """
        Check if this appears to be an extracted fzpz structure.
        In fzpz files, SVGs are in the same directory as the FZP.
        """
        dir_path = os.path.dirname(fzp_path)
        svg_in_same_dir = os.path.isfile(os.path.join(dir_path, image))
        
        # Also check if we don't have the standard fritzing-parts directory structure
        up_one_level = os.path.dirname(dir_path)
        svg_in_standard_location = os.path.isfile(os.path.join(up_one_level, 'svg', 'core', image))
        
        return svg_in_same_dir and not svg_in_standard_location

    @staticmethod
    def extract_fzpz(fzpz_path, extract_to=None):
        """
        Extract an fzpz file to a temporary or specified directory.
        Returns the path to the extracted FZP file.
        """
        if not fzpz_path.endswith('.fzpz'):
            raise ValueError("File must have .fzpz extension")
        
        if not os.path.isfile(fzpz_path):
            raise FileNotFoundError(f"FZPZ file not found: {fzpz_path}")
        
        if extract_to is None:
            extract_to = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(fzpz_path, 'r') as zip_file:
                FZPUtils._validate_zip_paths(zip_file, fzpz_path)
                
                zip_file.extractall(extract_to)
                
                # Find the FZP file in the extracted contents
                for filename in os.listdir(extract_to):
                    if filename.endswith('.fzp'):
                        return os.path.join(extract_to, filename)
                
                raise ValueError("No FZP file found in FZPZ archive")
                
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid FZPZ file: {fzpz_path}")

    @staticmethod
    def _validate_zip_paths(zip_file, fzpz_path):
        """
        Validate all paths in the zip file to prevent directory traversal attacks.
        Raises ValueError if any unsafe paths are found.
        """
        unsafe_paths = []
        
        for member in zip_file.infolist():
            path = member.filename
            
            # Check for absolute paths
            if os.path.isabs(path):
                unsafe_paths.append(f"Absolute path: {path}")
                continue
            
            # Check for directory traversal patterns
            if ".." in path:
                unsafe_paths.append(f"Directory traversal: {path}")
                continue
            
            # Normalize the path and check if it tries to escape the extraction directory
            normalized_path = os.path.normpath(path)
            if normalized_path.startswith("..") or os.path.isabs(normalized_path):
                unsafe_paths.append(f"Path escape attempt: {path}")
                continue
        
        if unsafe_paths:
            error_msg = f"Security violation in FZPZ file '{fzpz_path}': " + "; ".join(unsafe_paths)
            raise ValueError(error_msg)

    @staticmethod
    def cleanup_extraction(extracted_dir):
        """
        Clean up extracted fzpz contents.
        """
        if os.path.exists(extracted_dir):
            shutil.rmtree(extracted_dir)

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