import unittest
import os
import sys
from io import StringIO
from .fzp_checker_runner import FZPCheckerRunner, AVAILABLE_CHECKERS, SVG_AVAILABLE_CHECKERS

class TestCheckers(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = 'test_data/core'
        self.verbose = True

    def test_valid_xml(self):
        fzp_file = os.path.join(self.test_data_dir, 'valid_xml.fzp.test')
        checker_runner = FZPCheckerRunner(fzp_file, verbose=self.verbose)

        captured_output = StringIO()
        sys.stdout = captured_output
        checker_runner.check([], [])
        sys.stdout = sys.__stdout__

        self.assertEqual(checker_runner.total_errors, 0)
        self.assertNotIn('Invalid XML', captured_output.getvalue())

    def test_invalid_xml(self):
        fzp_file = os.path.join(self.test_data_dir, 'invalid_xml.fzp.test')
        checker_runner = FZPCheckerRunner(fzp_file, verbose=self.verbose)

        captured_output = StringIO()
        sys.stdout = captured_output
        checker_runner.check([], [])
        sys.stdout = sys.__stdout__

        self.assertEqual(checker_runner.total_errors, 1)
        self.assertIn('Invalid XML', captured_output.getvalue())

    def run_checker(self, fzp_filename, fzp_checkers, svg_checkers, expected_errors, expected_message, expected_warnings=None):
        fzp_file = os.path.join(self.test_data_dir, fzp_filename)
        checker_runner = FZPCheckerRunner(fzp_file, verbose=self.verbose)

        # Run specific FZP and SVG checkers for this test case
        checker_runner.check(fzp_checkers, svg_checkers)

        self.assertEqual(expected_errors, checker_runner.total_errors)
        if expected_warnings is not None:
            self.assertEqual(expected_warnings, checker_runner.total_warnings)

    def test_pcb_only_part(self):
        self.run_checker('pcb_only.fzp.test',
                         ['missing_tags','connector_terminal','connector_visibility'],
                         ['font_size','viewbox','ids'], 0, None)

    def test_hybrid_connectors_part(self):
        self.run_checker('hybrid_connectors.fzp.test',
                         ['missing_tags','connector_terminal','connector_visibility'],
                         ['font_size','viewbox','ids'], 7, None)
        # Expected errors:
        # connector0 to 5 are covered, but it is not yet specified how
        # this could be supported by Fritzing in a cleaner way.
        # connector9 is really not visible, and therefore rendered incorrect, which is the issue we want to report
        # with the invisible_connectors test.
        # Invisible connector 'connector0pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector1pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector2pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector3pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector4pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector5pin' in layer 'breadboard' of file 'test_data/core/hybrid_connectors.fzp.test'
        # Invisible connector 'connector9pin' in layer 'copper1' of file 'test_data/core/hybrid_connectors.fzp.test'

    def test_css_connector_part(self):
        self.run_checker('css_connector.fzp.test',
                         ['connector_terminal','connector_visibility'],
                         [], 3, None)
        # Expected errors:
        # Error in connector2invalid_style : Unknown style attribute: something
        # Error in connector3invalid_style : not enough values to unpack (expected 2, got 1)
        # Invisible connector 'connector4invisible' in layer 'copper0' of file 'test_data/core/css_connector.fzp.test'


    def test_font_size(self):
        self.run_checker('font_size.fzp.test',
                         [], ['font_size'], 4, None)
        # Expected errors:
        # No font size found for element [
        #         Test No Font Size 1
        #     ]
        # No font size found for element [ Test No Font Size 2 ]
        # Invalid font size 5px unit in element: [
        #          Test px unit
        #      ]
        # Invalid font size 2mm unit in element: [
        #          Test mm unit
        #      ]



    # def test_missing_tags(self):
    #     self.run_checker('missing_tags.fzp.test', ['missing_tags'], [], 1, 'Missing required tag')
    #
    # def test_invalid_terminal(self):
    #     self.run_checker('invalid_terminal.fzp.test', ['connector_terminal'], [], 1, 'references missing terminal')
    #
    # def test_invisible_connector(self):
    #     self.run_checker('invisible_connector.fzp.test', ['connector_visibility'], [], 1, 'Invisible connector')

    def test_stroke_checker(self):
        self.run_checker('stroke_test.fzp.test',
                         ['pcb_connector_stroke'], [], 2, None)

    def test_missing_connector_refs(self):
        self.run_checker('missing_connector_refs.fzp.test',
                        ['missing_connector_refs'],
                        [], 4, None)  # 4 errors: 2 copper0, 1 breadboard, 1 schematic

    def test_connector_refs_valid(self):
        self.run_checker('connector_refs_valid.fzp.test',
                        ['missing_connector_refs'],
                        [], 0, None)  # No errors when all references are present

    def test_missing_leg_ids(self):
        self.run_checker('missing_leg_ids.fzp.test',
                        ['missing_leg_ids'],
                        [], 2, None)  # 2 errors for missing leg refs

    def test_fritzing_version_present_valid(self):
        self.run_checker('fritzing_version_present_valid.fzp.test',
                         ['fritzing_version'],
                         [], 0, None, 0)

    def test_fritzing_version_missing(self):
        self.run_checker('fritzing_version_missing.fzp.test',
                         ['fritzing_version'],
                         [], 1, None, 0)

    def test_fritzing_version_missing(self):
        self.run_checker('fritzing_version_invalid_format.fzp.test',
                         ['fritzing_version'],
                         [], 1, None, 0)

    def test_module_id_present(self):
        self.run_checker('module_id_present.fzp.test',
                         ['module_id'],
                         [], 0, None, 0)

    def test_module_id_missing(self):
        self.run_checker('module_id_missing.fzp.test',
                         ['module_id'],
                         [], 1, None, 0)

    def test_module_id_special_chars_present(self):
        self.run_checker('module_id_special_chars_present.fzp.test',
                         ['module_id_special_chars'],
                         [], 0, None, 1)  # 1 warning for '*'

    def test_module_id_special_chars_absent(self):
        self.run_checker('module_id_special_chars_absent.fzp.test',
                         ['module_id_special_chars'],
                         [], 0, None, 0)

    def test_version_present_valid(self):
        self.run_checker('version_present_valid.fzp.test',
                         ['version'],
                         [], 0, None, 0)

    def test_version_missing(self):
        self.run_checker('version_missing.fzp.test',
                         ['version'],
                         [], 0, None, 1)

    def test_version_invalid_format(self):
        self.run_checker('version_invalid_format.fzp.test',
                         ['version'],
                         [], 0, None, 1)

    def test_title_present(self):
        self.run_checker('title_present.fzp.test',
                         ['title'],
                         [], 0, None, 0)

    def test_title_missing(self):
        self.run_checker('title_missing.fzp.test',
                         ['title'],
                         [], 1, None, 0)

    def test_description_present(self):
        self.run_checker('description_present.fzp.test',
                         ['description'],
                         [], 0, None, 0)

    def test_description_missing(self):
        self.run_checker('description_missing.fzp.test',
                         ['description'],
                         [], 0, None, 1)

    def test_author_present(self):
        self.run_checker('author_present.fzp.test',
                         ['author'],
                         [], 0, None, 0)

    def test_author_missing(self):
        self.run_checker('author_missing.fzp.test',
                         ['author'],
                         [], 0, None, 1)

    def test_required_tags_present(self):
        self.run_checker('required_tags_present.fzp.test',
                         ['required_tags'],
                         [], 4, None, 0)

    def test_required_tags_missing(self):
        self.run_checker('required_tags_missing.fzp.test',
                         ['required_tags'],
                         [], 6, None, 0)

    def test_family_property_present_and_valid(self):
        self.run_checker('family_property_present_valid.fzp.test',
                         ['family_property'],
                         [], 0, None, 0)

    def test_family_property_missing(self):
        self.run_checker('family_property_missing.fzp.test',
                         ['family_property'],
                         [], 1, None, 0)

    def test_unique_property_names_unique(self):
        self.run_checker('unique_property_names_unique.fzp.test',
                         ['unique_property_names'],
                         [], 0, None, 0)

    def test_unique_property_names_duplicates(self):
        self.run_checker('unique_property_names_duplicates.fzp.test',
                         ['unique_property_names'],
                         [], 1, None, 0)

    def test_property_fields_present(self):
        self.run_checker('property_fields_present.fzp.test',
                         ['property_fields'],
                         [], 0, None, 0)

    def test_property_fields_missing_name(self):
        self.run_checker('property_fields_missing_name.fzp.test',
                         ['property_fields'],
                         [], 1, None, 0)

    def test_property_fields_missing_value(self):
        self.run_checker('property_fields_missing_value.fzp.test',
                         ['property_fields'],
                         [], 1, None, 0)

    def test_views_present(self):
        self.run_checker('views_present.fzp.test',
                         ['views'],
                         [], 3, None, 0)

    def test_views_missing(self):
        self.run_checker('views_missing.fzp.test',
                         ['views'],
                         [], 1, None, 0)

    def test_buses_present_valid(self):
        self.run_checker('buses_present_valid.fzp.test',
                         ['buses'],
                         [], 0, None, 0)

    def test_buses_missing_id(self):
        self.run_checker('buses_missing_id.fzp.test',
                         ['buses'],
                         [], 1, None, 0)

    def test_buses_missing_node_members(self):
        self.run_checker('buses_missing_node_members.fzp.test',
                         ['buses'],
                         [], 1, None, 0)

    def test_connector_layers_present_valid(self):
        self.run_checker('connector_layers_present_valid.fzp.test',
                         ['connector_layers'],
                         [], 0, None, 0)

    def test_connector_layers_missing_attributes(self):
        self.run_checker('connector_layers_missing_attributes.fzp.test',
                         ['connector_layers'],
                         [], 7, None, 0)


    def test_layer_ids_match(self):
        self.run_checker('layer_ids_match.fzp.test',
                         ['layer_ids'],
                         [], 0, None)

    def test_layer_ids_mismatch(self):
        self.run_checker('layer_ids_mismatch.fzp.test',
                         ['layer_ids'],
                         [], 3, None)

    def test_matrix_transform(self):
        self.run_checker('matrix_transform.fzp.test',
                        [],
                        ['matrix'],
                        5,
                        None)

    def test_layer_nesting_valid(self):
        self.run_checker('layer_nesting_valid.fzp.test',
                        [],
                        ['layer_nesting'],
                        0,
                        None)

    def test_layer_nesting_invalid(self):
        self.run_checker('layer_nesting_invalid.fzp.test',
                        [],
                        ['layer_nesting'],
                        2,
                        None)

    def test_gorn_present(self):
        """Test that gorn attributes are detected in SVG files"""
        self.run_checker('gorn_present.fzp.test',
                         [],
                         ['svg-gorn'],
                         3,  # Should find 3 gorn attributes
                         None)

    def test_gorn_absent(self):
        """Test that files without gorn attributes pass the check"""
        self.run_checker('gorn_absent.fzp.test',
                         [],
                         ['svg-gorn'],
                         0,  # Should find no gorn attributes
                         None)

    def test_gorn_fix(self):
        """Test that gorn attributes can be automatically removed"""
        import tempfile
        import shutil
        
        # Create temporary copies of test files
        test_fzp = os.path.join(self.test_data_dir, 'gorn_present.fzp.test')
        test_svg = 'test_data/svg/core/breadboard/gorn_present_breadboard.svg'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy test files to temp directory
            temp_fzp = os.path.join(temp_dir, 'temp_gorn.fzp')
            temp_svg = os.path.join(temp_dir, 'temp_gorn.svg')
            
            shutil.copy(test_fzp, temp_fzp)
            shutil.copy(test_svg, temp_svg)
            
            # Update FZP to reference temp SVG
            with open(temp_fzp, 'r') as f:
                content = f.read()
            content = content.replace('gorn_present_breadboard.svg', 'temp_gorn.svg')
            with open(temp_fzp, 'w') as f:
                f.write(content)
            
            # Test initial state - should have gorn attributes
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['svg-gorn'], fix=False)
            self.assertEqual(checker_runner.total_errors, 3, "Should initially have 3 gorn errors")
            
            # Apply fix
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['svg-gorn'], fix=True)
            
            # Check that fix was successful
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['svg-gorn'], fix=False)
            self.assertEqual(checker_runner.total_errors, 0, "Should have no gorn errors after fix")

    def test_unique_ids_valid(self):
        """Test that files with unique IDs pass the check"""
        self.run_checker('unique_ids.fzp.test',
                         [],
                         ['ids'],
                         0,  # Should find no duplicate IDs
                         None)

    def test_duplicate_ids_invalid(self):
        """Test that duplicate IDs are detected"""
        self.run_checker('duplicate_ids.fzp.test',
                         [],
                         ['ids'],
                         5,  # Should find 5 duplicate ID errors (5 elements with id="label")
                         None)

    def test_duplicate_ids_fix(self):
        """Test that duplicate label IDs can be automatically fixed"""
        import tempfile
        import shutil
        import re

        # Create temporary copies of test files
        test_fzp = os.path.join(self.test_data_dir, 'duplicate_ids.fzp.test')
        test_svg = 'test_data/svg/core/breadboard/duplicate_ids_breadboard.svg'

        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy test files to temp directory
            temp_fzp = os.path.join(temp_dir, 'temp_duplicate_ids.fzp')
            temp_svg = os.path.join(temp_dir, 'temp_duplicate_ids.svg')

            shutil.copy(test_fzp, temp_fzp)
            shutil.copy(test_svg, temp_svg)

            # Update FZP to reference temp SVG
            with open(temp_fzp, 'r') as f:
                content = f.read()
            content = content.replace('duplicate_ids_breadboard.svg', 'temp_duplicate_ids.svg')
            with open(temp_fzp, 'w') as f:
                f.write(content)

            # Test initial state - should have duplicate ID errors
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['ids'], fix=False)
            initial_errors = checker_runner.total_errors
            self.assertGreater(initial_errors, 0, "Should initially have duplicate ID errors")

            # Apply fix
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['ids'], fix=True)

            # Verify that the SVG was modified to combine consecutive text elements
            with open(temp_svg, 'r') as f:
                fixed_content = f.read()

            # Should have fewer text elements with id="label" after fix
            label_count = len(re.findall(r'id="label"', fixed_content))
            self.assertEqual(label_count, 2, "Should have 2 elements with id='label' after fix (1 combined text + 1 circle)")

            # Should have tspan elements
            tspan_count = len(re.findall(r'<tspan', fixed_content))
            self.assertGreater(tspan_count, 0, "Should have tspan elements after fix")

            # Check that fix reduced errors (though may not eliminate all due to non-text duplicates)
            checker_runner = FZPCheckerRunner(temp_fzp, verbose=False)
            checker_runner.check([], ['ids'], fix=False)
            final_errors = checker_runner.total_errors
            self.assertLess(final_errors, initial_errors, "Should have fewer duplicate ID errors after fix")

if __name__ == '__main__':
    unittest.main()
