# fzp_additional_checks.py
from lxml import etree

def check_bus_id(fzp_doc):
    buses = fzp_doc.findall('.//bus')
    errors = 0
    for bus in buses:
        bus_id = bus.get('id')
        if not bus_id:
            print(f"Bus with missing ID found: {etree.tostring(bus, pretty_print=True).decode()}")
            errors += 1
    return errors

def check_bus_nodes(fzp_doc):
    buses = fzp_doc.findall('.//bus')
    errors = 0
    for bus in buses:
        nodes = bus.findall('.//nodeMember')
        if not nodes:
            print(f"Bus with ID '{bus.get('id')}' has no node members.")
            errors += 1
        else:
            for node in nodes:
                connector_id = node.get('connectorId')
                if not connector_id:
                    print(f"BusNode with missing connectorId in Bus '{bus.get('id')}'.")
                    errors += 1
    return errors

def check_connector_layers(fzp_doc):
    connectors = fzp_doc.findall('.//connector')
    errors = 0
    for connector in connectors:
        layers = connector.findall('.//ConnectorLayer')
        for layer in layers:
            layer_id = layer.get('layer')
            svg_id = layer.get('svgId')
            terminal_id = layer.get('terminalId')

            if not layer_id:
                print(f"ConnectorLayer missing layer ID in Connector '{connector.get('id')}'.")
                errors += 1
            if not svg_id:
                print(f"ConnectorLayer missing svgId in Connector '{connector.get('id')}'.")
                errors += 1
            if not terminal_id:
                print(f"ConnectorLayer missing terminalId in Connector '{connector.get('id')}'.")
                errors += 1
    return errors

def check_family_property(fzp_doc):
    properties = fzp_doc.findall('.//property')
    family_found = False
    errors = 0
    for prop in properties:
        if prop.get('name') == 'family':
            if not prop.text:
                print("Property 'family' has no value.")
                errors += 1
            family_found = True
            break
    if not family_found:
        print("Property 'family' is missing.")
        errors += 1
    return errors

def check_unique_property_names(fzp_doc):
    properties = fzp_doc.findall('.//property')
    names = set()
    errors = 0
    for prop in properties:
        name = prop.get('name')
        if name in names:
            print(f"Duplicate property name found: '{name}'.")
            errors += 1
        else:
            names.add(name)
    return errors

def check_property_fields(fzp_doc):
    properties = fzp_doc.findall('.//property')
    errors = 0
    for prop in properties:
        name = prop.get('name')
        value = prop.text
        if not name:
            print(f"Property with missing name: {etree.tostring(prop, pretty_print=True).decode()}")
            errors += 1
        if not value:
            print(f"Property '{name}' has no value.")
            errors += 1
    return errors

def check_required_tags_and_attributes(fzp_doc):
    required_tags = {
        'module': ['moduleId'],
        'title': [],
        'tags': [],
        'properties': [],
        'views': [],
        'connectors': [],
        'buses': []
    }
    errors = 0
    for tag, attrs in required_tags.items():
        elements = fzp_doc.findall(f'.//{tag}')
        if not elements:
            print(f"Missing required tag: {tag}")
            errors += 1
        else:
            for attr in attrs:
                if not elements[0].get(attr):
                    print(f"Tag '{tag}' is missing required attribute '{attr}'.")
                    errors += 1
    return errors

def check_buses(fzp_doc):
    buses = fzp_doc.findall('.//bus')
    errors = 0
    for bus in buses:
        bus_id = bus.get('id')
        if not bus_id:
            print(f"Bus found without an ID: {etree.tostring(bus, pretty_print=True).decode()}")
            errors += 1
        node_members = bus.findall('.//nodeMember')
        if not node_members:
            print(f"Bus '{bus_id}' has no node members.")
            errors += 1
    return errors

# fzp_additional_checks.py

from lxml import etree
import re

def check_fritzing_version(fzp_doc):
    """
    Ensures that the FritzingVersion attribute is present and follows expected formatting.
    """
    root = fzp_doc.getroot()
    fritzing_version = root.get('fritzingVersion')

    if not fritzing_version:
        print("Error: 'FritzingVersion' is undefined or empty.")
        return 1  # Indicates one error

    # Validate the version format (e.g., semantic versioning)
    version_pattern = r'^\d+\.\d+(\.\d+)?$'  # Simple semantic versioning pattern
    if not re.match(version_pattern, fritzing_version.strip()):
        print(f"Error: 'FritzingVersion' '{fritzing_version}' does not match the expected format.")
        return 1

    return 0

def check_module_id(fzp_doc):
    """
    Ensures that the ModuleID attribute is present and non-empty.
    """
    root = fzp_doc.getroot()
    module_id = root.get('moduleId')

    if not module_id:
        print("Error: 'ModuleID' is undefined or empty.")
        return 1
    return 0

def check_version(fzp_doc):
    """
    Validates the Version attribute for correct formatting.
    """
    root = fzp_doc.getroot()
    version = root.findtext('version')

    if not version:
        # As per Go code, it's a warning, not an error
        print("Warning: 'Version' is undefined.")
        return 0  # No error increment
    # Validate version format
    version_pattern = r'^\d+\.\d+(\.\d+)?$'  # Simple semantic versioning
    if not re.match(version_pattern, version.strip()):
        print(f"Warning: 'Version' '{version}' does not match the expected format.")
    return 0  # Warnings do not increment error count

def check_title(fzp_doc):
    """
    Ensures that the Title attribute is present and non-empty.
    """
    root = fzp_doc.getroot()
    title = root.findtext('title')

    if not title:
        print("Error: 'Title' is undefined or empty.")
        return 1
    return 0

def check_description(fzp_doc):
    """
    Verifies that the Description attribute is present.
    """
    root = fzp_doc.getroot()
    description = root.findtext('description')

    if not description:
        # As per Go code, it's a warning, not an error
        print("Warning: 'Description' is undefined.")
    return 0  # Warnings do not increment error count

def check_author(fzp_doc):
    """
    Validates the presence of the Author attribute.
    """
    root = fzp_doc.getroot()
    author = root.findtext('author')

    if not author:
        # As per Go code, it's a warning, not an error
        print("Warning: 'Author' is undefined.")
    return 0  # Warnings do not increment error count

def check_required_tags_and_attributes(fzp_doc):
    """
    Validates the presence of all required tags and their mandatory attributes within the FZP file.
    """
    required_tags = {
        'module': ['moduleId'],
        'title': [],
        'tags': [],
        'properties': [],
        'views': [],
        'connectors': [],
        'buses': []
    }
    errors = 0
    root = fzp_doc.getroot()
    for tag, attrs in required_tags.items():
        elements = fzp_doc.findall('.//' + tag)
        if not elements:
            print(f"Error: Required tag '{tag}' is missing.")
            errors += 1
            continue
        for attr in attrs:
            if not elements[0].get(attr):
                print(f"Error: Tag '{tag}' is missing required attribute '{attr}'.")
                errors += 1
    return errors

def check_family_property(fzp_doc):
    """
    Ensures that the 'family' property exists and is non-empty.
    """
    properties = fzp_doc.findall('.//property')
    family_found = False
    errors = 0
    for prop in properties:
        if prop.get('name') == 'family':
            family_found = True
            if not prop.text or not prop.text.strip():
                print("Error: 'family' property is defined but empty.")
                errors += 1
            break
    if not family_found:
        print("Error: 'family' property is missing.")
        errors += 1
    return errors

def check_unique_property_names(fzp_doc):
    """
    Ensures that all property names are unique.
    """
    properties = fzp_doc.findall('.//property')
    names = set()
    errors = 0
    for prop in properties:
        name = prop.get('name')
        if not name:
            print("Error: A property is missing the 'name' attribute.")
            errors += 1
            continue
        if name in names:
            print(f"Error: Duplicate property name found: '{name}'.")
            errors += 1
        else:
            names.add(name)
    return errors

def check_property_fields(fzp_doc):
    """
    Ensures that each property has a non-empty name and value.
    """
    properties = fzp_doc.findall('.//property')
    errors = 0
    for prop in properties:
        name = prop.get('name')
        value = prop.text.strip() if prop.text else ''
        if not name:
            print(f"Error: Property with empty 'name' attribute found: {etree.tostring(prop, pretty_print=True).decode()}")
            errors += 1
        if not value:
            print(f"Error: Property '{name}' has an empty value.")
            errors += 1
    return errors

def check_views(fzp_doc):
    """
    Ensures that all required views are properly defined.
    """
    views = fzp_doc.findall('.//views')
    required_views = ['iconView', 'breadboardView', 'pcbView', 'schematicView']
    errors = 0
    if not views:
        print("Error: 'views' section is missing.")
        return 1
    for view in required_views:
        if view not in [child.tag for child in views[0]]:
            print(f"Error: Required view '{view}' is missing.")
            errors += 1
    return errors

def check_buses(fzp_doc):
    """
    Ensures that all buses have non-empty IDs and contain at least one valid BusNode.
    """
    buses = fzp_doc.findall('.//bus')
    errors = 0
    for bus in buses:
        bus_id = bus.get('id')
        if not bus_id:
            print(f"Error: Bus with missing ID found: {etree.tostring(bus, pretty_print=True).decode()}")
            errors += 1
        node_members = bus.findall('.//nodeMember')
        if not node_members:
            print(f"Error: Bus '{bus_id}' has no node members.")
            errors += 1
        else:
            for node in node_members:
                connector_id = node.get('connectorId')
                if not connector_id:
                    print(f"Error: BusNode in Bus '{bus_id}' has empty 'connectorId'.")
                    errors += 1
    return errors

def check_connector_layers(fzp_doc):
    """
    Ensures that each ConnectorLayer within a Connector has valid LayerID, SvgID, and TerminalID.
    """
    connectors = fzp_doc.findall('.//connector')
    errors = 0
    for connector in connectors:
        layers = connector.findall('.//ConnectorLayer')
        for layer in layers:
            layer_id = layer.get('layer')
            svg_id = layer.get('svgId')
            terminal_id = layer.get('terminalId')

            if not layer_id:
                print(f"Error: ConnectorLayer missing 'layer' ID in Connector '{connector.get('id')}'.")
                errors += 1
            if not svg_id:
                print(f"Error: ConnectorLayer missing 'svgId' in Connector '{connector.get('id')}'.")
                errors += 1
            if not terminal_id:
                print(f"Error: ConnectorLayer missing 'terminalId' in Connector '{connector.get('id')}'.")
                errors += 1
    return errors
