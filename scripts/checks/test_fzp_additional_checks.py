# test_fzp_additional_checks.py

import unittest
from lxml import etree
from fzp_additional_checks import (
    check_fritzing_version,
    check_module_id,
    check_version,
    check_title,
    check_description,
    check_author,
    check_required_tags,
    check_views,
    check_bus_id,
    check_bus_nodes,
    check_connector_layers,
    check_family_property,
    check_unique_property_names,
    check_property_fields,
    check_required_tags_and_attributes,
    check_buses

)

class TestFZPAdditionalChecks(unittest.TestCase):
    def test_fritzing_version_present_valid(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <tags>
                <tag>Test</tag>
            </tags>
            <properties>
                <property name="family">TestFamily</property>
            </properties>
            <views>
                <iconView>...</iconView>
                <breadboardView>...</breadboardView>
                <pcbView>...</pcbView>
                <schematicView>...</schematicView>
            </views>
            <connectors>
                <!-- Connector definitions -->
            </connectors>
            <buses>
                <!-- Bus definitions -->
            </buses>
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_fritzing_version(fzp_doc)
        self.assertEqual(errors, 0)

    def test_fritzing_version_missing(self):
        xml_content = """
        <module moduleId="test_module">
            <title>Test Module</title>
            <tags>
                <tag>Test</tag>
            </tags>
            <properties>
                <property name="family">TestFamily</property>
            </properties>
            <views>
                <iconView>...</iconView>
                <breadboardView>...</breadboardView>
                <pcbView>...</pcbView>
                <schematicView>...</schematicView>
            </views>
            <connectors>
                <!-- Connector definitions -->
            </connectors>
            <buses>
                <!-- Bus definitions -->
            </buses>
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_fritzing_version(fzp_doc)
        self.assertEqual(errors, 1)

    def test_fritzing_version_invalid_format(self):
        xml_content = """
        <module fritzingVersion="v1" moduleId="test_module">
            <title>Test Module</title>
            <tags>
                <tag>Test</tag>
            </tags>
            <properties>
                <property name="family">TestFamily</property>
            </properties>
            <views>
                <iconView>...</iconView>
                <breadboardView>...</breadboardView>
                <pcbView>...</pcbView>
                <schematicView>...</schematicView>
            </views>
            <connectors>
                <!-- Connector definitions -->
            </connectors>
            <buses>
                <!-- Bus definitions -->
            </buses>
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_fritzing_version(fzp_doc)
        self.assertEqual(errors, 1)

    def test_module_id_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_module_id(fzp_doc)
        self.assertEqual(errors, 0)

    def test_module_id_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3">
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_module_id(fzp_doc)
        self.assertEqual(errors, 1)

    def test_version_present_valid(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <version>2.1.0</version>
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_version(fzp_doc)
        self.assertEqual(errors, 0)

    def test_version_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_version(fzp_doc)
        self.assertEqual(errors, 0)  # Warning does not count as error

    def test_version_invalid_format(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <version>v2</version>
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_version(fzp_doc)
        self.assertEqual(errors, 0)  # Warning does not count as error

    def test_title_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_title(fzp_doc)
        self.assertEqual(errors, 0)

    def test_title_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <!-- Title is missing -->
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_title(fzp_doc)
        self.assertEqual(errors, 1)

    def test_description_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <description>This is a test module.</description>
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_description(fzp_doc)
        self.assertEqual(errors, 0)

    def test_description_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <!-- Description is missing -->
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_description(fzp_doc)
        self.assertEqual(errors, 0)  # Warning does not count as error

    def test_author_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <author>Jane Doe</author>
            <title>Test Module</title>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_author(fzp_doc)
        self.assertEqual(errors, 0)

    def test_author_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <!-- Author is missing -->
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_author(fzp_doc)
        self.assertEqual(errors, 0)  # Warning does not count as error

    def test_required_tags_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <title>Test Module</title>
            <tags>
                <tag>Test</tag>
            </tags>
            <properties>
                <property name="family">TestFamily</property>
            </properties>
            <views>
                <iconView>...</iconView>
                <breadboardView>...</breadboardView>
                <pcbView>...</pcbView>
                <schematicView>...</schematicView>
            </views>
            <connectors>
                <!-- Connector definitions -->
            </connectors>
            <buses>
                <!-- Bus definitions -->
            </buses>
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_required_tags_and_attributes(fzp_doc)
        self.assertEqual(errors, 0)

    def test_required_tags_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3">
            <!-- Missing moduleId, title, tags, properties, etc. -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_required_tags_and_attributes(fzp_doc)
        self.assertGreater(errors, 0)

    def test_family_property_present_and_valid(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property name="family">TestFamily</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_family_property(fzp_doc)
        self.assertEqual(errors, 0)

    def test_family_property_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <!-- 'family' property is missing -->
                <property name="other">Value</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_family_property(fzp_doc)
        self.assertEqual(errors, 1)

    def test_unique_property_names_unique(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property name="family">TestFamily</property>
                <property name="size">Medium</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_unique_property_names(fzp_doc)
        self.assertEqual(errors, 0)

    def test_unique_property_names_duplicates(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property name="family">TestFamily</property>
                <property name="family">AnotherFamily</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_unique_property_names(fzp_doc)
        self.assertEqual(errors, 1)

    def test_property_fields_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property name="family">TestFamily</property>
                <property name="size">Medium</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_property_fields(fzp_doc)
        self.assertEqual(errors, 0)

    def test_property_fields_missing_name(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property>ValueWithoutName</property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_property_fields(fzp_doc)
        self.assertEqual(errors, 1)

    def test_property_fields_missing_value(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <properties>
                <property name="family"></property>
            </properties>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_property_fields(fzp_doc)
        self.assertEqual(errors, 1)

    def test_views_present(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <views>
                <iconView>...</iconView>
                <breadboardView>...</breadboardView>
                <pcbView>...</pcbView>
                <schematicView>...</schematicView>
            </views>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_views(fzp_doc)
        self.assertEqual(errors, 0)

    def test_views_missing(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <!-- 'views' section is missing -->
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_views(fzp_doc)
        self.assertEqual(errors, 1)

    def test_buses_present_valid(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <buses>
                <bus id="bus1">
                    <nodeMember connectorId="connector1"/>
                </bus>
            </buses>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_buses(fzp_doc)
        self.assertEqual(errors, 0)

    def test_buses_missing_id(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <buses>
                <bus>
                    <nodeMember connectorId="connector1"/>
                </bus>
            </buses>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_buses(fzp_doc)
        self.assertEqual(errors, 1)

    def test_buses_missing_node_members(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <buses>
                <bus id="bus1">
                    <!-- nodeMember is missing -->
                </bus>
            </buses>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_buses(fzp_doc)
        self.assertEqual(errors, 1)

    def test_connector_layers_present_valid(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <connectors>
                <connector id="conn1">
                    <ConnectorLayer layer="layer1" svgId="svg1" terminalId="term1"/>
                </connector>
            </connectors>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_connector_layers(fzp_doc)
        self.assertEqual(errors, 0)

    def test_connector_layers_missing_attributes(self):
        xml_content = """
        <module fritzingVersion="1.0.3" moduleId="test_module">
            <connectors>
                <connector id="conn1">
                    <ConnectorLayer layer="" svgId="svg1" terminalId="term1"/>
                    <ConnectorLayer layer="layer2" svgId="" terminalId="term2"/>
                    <ConnectorLayer layer="layer3" svgId="svg3" terminalId=""/>
                </connector>
            </connectors>
            <!-- Other required tags -->
        </module>
        """
        fzp_doc = etree.fromstring(xml_content)
        errors = check_connector_layers(fzp_doc)
        self.assertEqual(errors, 3)

if __name__ == '__main__':
    unittest.main()
