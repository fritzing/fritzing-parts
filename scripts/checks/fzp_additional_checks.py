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
