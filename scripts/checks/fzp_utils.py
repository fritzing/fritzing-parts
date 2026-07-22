import os
import re
import zipfile
import tempfile
import shutil
from lxml import etree

class FZPUtils:
    # Views whose connectors reference SVG element ids (iconView never does)
    CONNECTOR_VIEWS = ('breadboardView', 'schematicView', 'pcbView')

    @staticmethod
    def get_referenced_connector_ids(fzp_doc, view_name):
        """
        All svgId/terminalId/legId values referenced by connector <p> elements
        for view_name. References of other views sharing the same SVG file are
        included. Returns None for views that never reference connectors
        (e.g. iconView).
        """
        if view_name not in FZPUtils.CONNECTOR_VIEWS:
            return None

        images = {}
        for view in FZPUtils.CONNECTOR_VIEWS:
            layers = fzp_doc.xpath(f"//views/{view}/layers")
            if layers:
                images[view] = layers[0].attrib.get("image")

        referenced = set()
        image = images.get(view_name)
        for view in FZPUtils.CONNECTOR_VIEWS:
            if view != view_name and (image is None or images.get(view) != image):
                continue
            for p in fzp_doc.xpath(f"//connector/views/{view}/p"):
                for attr in ('svgId', 'terminalId', 'legId'):
                    value = p.attrib.get(attr)
                    if value:
                        referenced.add(value)
        return referenced

    @staticmethod
    def find_fzp_dir_for_svg(svg_path):
        """
        For an SVG in a parts repository layout (<root>/svg/<family>/<view>/file.svg),
        return the matching FZP directory <root>/<family>, or None.
        """
        abs_path = os.path.abspath(svg_path)
        parts = abs_path.split(os.sep)
        for index in range(len(parts) - 2, 0, -1):
            if parts[index] == 'svg':
                fzp_dir = os.sep.join(parts[:index] + [parts[index + 1]])
                if os.path.isdir(fzp_dir):
                    return fzp_dir
        return None

    @staticmethod
    def find_referenced_connector_ids_for_svg(svg_path, fzp_dir=None):
        """
        Union of connector ids referenced by all FZP files whose views use this
        SVG. Returns None if no parts directory or no referencing FZP is found
        (usage cannot be judged then), or if the SVG is only used as icon.
        """
        if fzp_dir is None:
            fzp_dir = FZPUtils.find_fzp_dir_for_svg(svg_path)
        if fzp_dir is None:
            return None

        svg_filename = os.path.basename(svg_path)
        referenced = None
        for root, dirs, files in os.walk(fzp_dir):
            for file in files:
                if not file.endswith('.fzp'):
                    continue
                fzp_path = os.path.join(root, file)
                try:
                    with open(fzp_path, 'r', encoding='utf-8') as f:
                        if svg_filename not in f.read():
                            continue
                    fzp_doc = etree.parse(fzp_path)
                except (OSError, UnicodeDecodeError, etree.XMLSyntaxError):
                    continue
                for view in FZPUtils.CONNECTOR_VIEWS:
                    layers = fzp_doc.xpath(f"//views/{view}/layers")
                    if not layers:
                        continue
                    image = layers[0].attrib.get("image") or ''
                    if os.path.basename(image) != svg_filename:
                        continue
                    view_refs = FZPUtils.get_referenced_connector_ids(fzp_doc, view)
                    referenced = view_refs if referenced is None else referenced | view_refs
        return referenced

    @staticmethod
    def get_svg_path(fzp_path, image, view_name):
        dir_path = os.path.dirname(fzp_path)
        
        # Check if this is an extracted fzpz structure (SVGs in same directory as FZP)
        is_fzpz_structure = FZPUtils.is_fzpz_structure(fzp_path, image)
        
        if is_fzpz_structure:
            # For fzpz files, check for the dot-prefixed naming conventions
            if '/' in image:
                # Try pattern: icon/file.svg -> icon.file.svg
                fzpz_filename = image.replace('/', '.')
                svg_path = os.path.join(dir_path, fzpz_filename)
                if os.path.isfile(svg_path):
                    # Skip template detection for fzpz files - process all SVGs
                    return svg_path
                    
                # Try pattern: icon/file.svg -> svg.icon.file.svg
                fzpz_filename = 'svg.' + image.replace('/', '.')
                svg_path = os.path.join(dir_path, fzpz_filename)
                if os.path.isfile(svg_path):
                    # Skip template detection for fzpz files - process all SVGs
                    return svg_path
            
            # Fall back to checking basename only
            image_filename = os.path.basename(image)
            svg_path = os.path.join(dir_path, image_filename)
            if os.path.isfile(svg_path):
                # Skip template detection for fzpz files - process all SVGs
                return svg_path
        else:
            # Standard fritzing-parts structure
            up_one_level = os.path.dirname(dir_path)
            
            # Try contrib first (for imported parts), then core
            svg_path_contrib = os.path.join(up_one_level, 'svg', 'contrib', image)
            if os.path.isfile(svg_path_contrib):
                # Contrib parts cannot be templates, so return the path directly
                return svg_path_contrib
            else:
                # Fall back to core directory
                svg_path = os.path.join(up_one_level, 'svg', 'core', image)
                # Only check templates for core parts
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
        FZPZ files use a naming convention where subdirectory/file.svg becomes subdirectory.file.svg
        """
        dir_path = os.path.dirname(fzp_path)
        
        # First check if the image file exists as-is (just the basename)
        image_filename = os.path.basename(image)
        svg_in_same_dir = os.path.isfile(os.path.join(dir_path, image_filename))
        
        # If not found, check for the fzpz naming conventions:
        # 1. subdirectory/file.svg becomes subdirectory.file.svg
        # 2. subdirectory/file.svg becomes svg.subdirectory.file.svg
        if not svg_in_same_dir and '/' in image:
            # Try pattern: icon/file.svg -> icon.file.svg
            fzpz_filename = image.replace('/', '.')
            svg_in_same_dir = os.path.isfile(os.path.join(dir_path, fzpz_filename))
            
            # Try pattern: icon/file.svg -> svg.icon.file.svg
            if not svg_in_same_dir:
                fzpz_filename = 'svg.' + image.replace('/', '.')
                svg_in_same_dir = os.path.isfile(os.path.join(dir_path, fzpz_filename))
        
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