import unittest
import os
import sys
from io import StringIO
from .fzp_checker_runner import FZPCheckerRunner, AVAILABLE_CHECKERS, SVG_AVAILABLE_CHECKERS
import tempfile
import shutil
from lxml import etree
from .svg_checkers import SVGIdsChecker


class TestCheckers(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = 'test_data/core'
        self.verbose = True

    def test_valid_xml(self):
        fzp_file = os.path.join(self.test_data_dir, 'valid_xml.fzp.test')
        checker_runner = FZPCheckerRunner(fzp_file)

        captured_output = StringIO()
        sys.stdout = captured_output
        checker_runner.check([], [])
        sys.stdout = sys.__stdout__

        # 4 missing SVG file errors (test data doesn't include the referenced SVGs)
        self.assertEqual(checker_runner.total_errors, 4)
        self.assertNotIn('Invalid XML', captured_output.getvalue())

    def test_invalid_xml(self):
        fzp_file = os.path.join(self.test_data_dir, 'invalid_xml.fzp.test')
        checker_runner = FZPCheckerRunner(fzp_file)

        checker_runner.check([], [])

        self.assertEqual(checker_runner.total_errors, 1)
        # Check that the error is recorded in the errors list
        self.assertTrue(len(checker_runner.all_issues) > 0)
        error_messages = [issue.message for issue in checker_runner.all_issues]
        self.assertTrue(any('Invalid XML' in msg for msg in error_messages))

    def run_checker(self, fzp_filename, fzp_checkers, svg_checkers, expected_errors, expected_message, expected_warnings=None):
        fzp_file = os.path.join(self.test_data_dir, fzp_filename)
        checker_runner = FZPCheckerRunner(fzp_file)

        # Run specific FZP and SVG checkers for this test case
        checker_runner.check(fzp_checkers, svg_checkers)

        self.assertEqual(expected_errors, checker_runner.total_errors)
        if expected_warnings is not None:
            self.assertEqual(expected_warnings, checker_runner.total_warnings)

    def test_pcb_only_part(self):
        self.run_checker('pcb_only.fzp.test',
                         ['missing_tags','connector_terminal','connector_svg_ref'],
                         ['font_size','viewbox','ids'], 0, None)

    def test_hybrid_connectors_part(self):
        self.run_checker('hybrid_connectors.fzp.test',
                         ['missing_tags','connector_terminal','connector_svg_ref'],
                         ['font_size','viewbox','ids'], 0, None)
        # The errors are now 0 after the invisibility check has been removed.

    def test_css_connector_part(self):
        self.run_checker('css_connector.fzp.test',
                         ['connector_terminal','connector_svg_ref'],
                         [], 0, None)
        # The errors are now 0 after the invisibility check has been removed.

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

    def test_font_size_fix(self):
        """Test that font-size unit suffixes are automatically removed"""
        test_svg = 'test_data/svg/core/pcb/font_size.svg'

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_svg = os.path.join(temp_dir, 'temp_font_size.svg')
            shutil.copy(test_svg, temp_svg)

            # Parse and check - should find unit errors
            svg_doc = etree.parse(temp_svg)
            from .svg_checkers import SVGFontSizeChecker
            checker = SVGFontSizeChecker(svg_doc, ['silkscreen'])
            errors, warnings = checker.check()
            self.assertGreater(errors, 0, "Should initially have font-size errors")

            # Apply fix
            fix_results = checker.fix(temp_svg)
            self.assertGreater(len(fix_results), 0, "Should have applied fixes")

            # Verify the file no longer has unit suffixes
            with open(temp_svg, 'r') as f:
                content = f.read()
            self.assertNotIn('font-size="5px"', content)
            self.assertNotIn('font-size="2mm"', content)
            self.assertIn('font-size="5"', content)
            self.assertIn('font-size="2"', content)

            # Re-check: only the 2 "missing font-size" errors should remain
            svg_doc2 = etree.parse(temp_svg)
            checker2 = SVGFontSizeChecker(svg_doc2, ['silkscreen'])
            errors2, _ = checker2.check()
            self.assertEqual(errors2, 2, "After fix, only missing font-size errors should remain")

    # def test_missing_tags(self):
    #     self.run_checker('missing_tags.fzp.test', ['missing_tags'], [], 1, 'Missing required tag')
    #
    # def test_invalid_terminal(self):
    #     self.run_checker('invalid_terminal.fzp.test', ['connector_terminal'], [], 1, 'references missing terminal')
    #
    # def test_invisible_connector(self):
    #     self.run_checker('invisible_connector.fzp.test', ['connector_svg_ref'], [], 1, 'Invisible connector')

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

    def _make_fzp_tree(self, xml_string):
        """Helper: parse XML string into an ElementTree (as FZPChecker expects)"""
        root = etree.fromstring(xml_string)
        return etree.ElementTree(root)

    def test_fritzing_version_range_current(self):
        """Test that version >= 1.0.4 passes without issues"""
        from .fzp_checkers import FZPFritzingVersionRangeChecker
        fzp_doc = self._make_fzp_tree('<module fritzingVersion="1.0.4" moduleId="test"/>')
        checker = FZPFritzingVersionRangeChecker(fzp_doc)
        errors, warnings = checker.check()
        self.assertEqual(errors, 0)
        self.assertEqual(warnings, 0)

    def test_fritzing_version_range_outdated_conventions(self):
        """Test that version < 1.0.4 but >= 0.9.4 warns about outdated conventions"""
        from .fzp_checkers import FZPFritzingVersionRangeChecker
        fzp_doc = self._make_fzp_tree('<module fritzingVersion="1.0.3" moduleId="test"/>')
        checker = FZPFritzingVersionRangeChecker(fzp_doc)
        errors, warnings = checker.check()
        self.assertEqual(errors, 0)
        self.assertEqual(warnings, 1)
        self.assertIn("outdated conventions", checker.issues[0].message)

    def test_fritzing_version_range_very_old(self):
        """Test that version < 0.8 produces error + ten years old warning"""
        from .fzp_checkers import FZPFritzingVersionRangeChecker
        fzp_doc = self._make_fzp_tree('<module fritzingVersion="0.5.2b.02.18.4756" moduleId="test"/>')
        checker = FZPFritzingVersionRangeChecker(fzp_doc)
        errors, warnings = checker.check()
        self.assertEqual(errors, 1)
        self.assertEqual(warnings, 1)
        error_msgs = [i.message for i in checker.issues if i.severity == 'error']
        warning_msgs = [i.message for i in checker.issues if i.severity == 'warning']
        self.assertIn("below 0.8", error_msgs[0])
        self.assertIn("ten years old", warning_msgs[0])

    def test_fritzing_version_range_at_threshold(self):
        """Test that version exactly 0.9.4 gets the outdated conventions warning"""
        from .fzp_checkers import FZPFritzingVersionRangeChecker
        fzp_doc = self._make_fzp_tree('<module fritzingVersion="0.9.4" moduleId="test"/>')
        checker = FZPFritzingVersionRangeChecker(fzp_doc)
        errors, warnings = checker.check()
        self.assertEqual(errors, 0)
        self.assertEqual(warnings, 1)
        self.assertIn("outdated conventions", checker.issues[0].message)

    def test_module_id_present(self):
        self.run_checker('module_id_present.fzp.test',
                         ['module_id'],
                         [], 0, None, 0)

    def test_module_id_missing(self):
        self.run_checker('module_id_missing.fzp.test',
                         ['module_id'],
                         [], 1, None, 0)

    def test_module_id_unsafe_filename_chars(self):
        self.run_checker('module_id_special_chars_present.fzp.test',
                         ['module_id_special_chars'],
                         [], 1, None, 0)  # 1 error for '*' (unsafe for filenames)

    def test_module_id_clean(self):
        self.run_checker('module_id_special_chars_absent.fzp.test',
                         ['module_id_special_chars'],
                         [], 0, None, 0)

    def test_module_id_non_alnum_warns(self):
        self.run_checker('module_id_non_alnum.fzp.test',
                         ['module_id_special_chars'],
                         [], 0, None, 1)  # 1 warning for space

    def test_module_id_too_short(self):
        self.run_checker('module_id_too_short.fzp.test',
                         ['module_id_special_chars'],
                         [], 1, None, 0)  # 1 error for too short (<8 chars)

    def test_module_id_special_chars_fix(self):
        """Test that the fixer replaces unsafe and non-alnum chars with underscores."""
        import tempfile
        import shutil
        src = os.path.join(self.test_data_dir, 'module_id_special_chars_present.fzp.test')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fzp', delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copy2(src, tmp_path)
        try:
            runner = FZPCheckerRunner(tmp_path)
            runner.check(['module_id_special_chars'], [], fix=True)
            with open(tmp_path, 'r', encoding='UTF-8') as f:
                content = f.read()
            self.assertIn('moduleId="SparkFun-DigitalIC-74_08-SE"', content)
        finally:
            os.unlink(tmp_path)

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
                         [], 4, None, 0)


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
            checker_runner = FZPCheckerRunner(temp_fzp)
            checker_runner.check([], ['svg-gorn'], fix=False)
            self.assertEqual(checker_runner.total_errors, 3, "Should initially have 3 gorn errors")
            
            # Apply fix
            checker_runner = FZPCheckerRunner(temp_fzp)
            checker_runner.check([], ['svg-gorn'], fix=True)
            
            # Check that fix was successful
            checker_runner = FZPCheckerRunner(temp_fzp)
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

        # Use the test SVG file directly
        test_svg = 'test_data/svg/core/breadboard/duplicate_ids_breadboard.svg'

        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy SVG to temp directory
            temp_svg = os.path.join(temp_dir, 'temp_duplicate_ids.svg')
            shutil.copy(test_svg, temp_svg)

            # Parse the SVG
            svg_doc = etree.parse(temp_svg)
            
            # Create the checker directly
            checker = SVGIdsChecker(svg_doc, [])

            # Test initial state - should have duplicate ID errors
            initial_errors, initial_warnings = checker.check()
            self.assertGreater(initial_errors, 0, "Should initially have duplicate ID errors")

            # Debug: Print the SVG content before fix to understand what we're working with
            with open(temp_svg, 'r') as f:
                before_content = f.read()
            print(f"DEBUG: SVG content before fix:")
            print(before_content)
            
            # Apply fix directly
            fix_results = checker.fix(temp_svg)
            
            # Debug output
            print(f"DEBUG: fix_results={fix_results}")
            print(f"DEBUG: fixes_count={checker.get_fixes_count()}")
            for fix in checker.fixes:
                print(f"DEBUG: Fix: {fix.message}")

            self.assertIsInstance(fix_results, list, "Fix method should return list of FixResult objects")
            self.assertGreater(len(fix_results), 0, "Should have applied some fixes - there are consecutive duplicate label IDs to fix")
            self.assertEqual(len(fix_results), checker.get_fixes_count(), "Fix results count should match fixes count")

    def test_date_format_valid_iso(self):
        """Test that valid ISO dates pass without changes"""
        fzp_xml = """<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>2024-06-13</date>
</module>"""

        from .fzp_checkers import FZPDateFormatChecker

        fzp_doc = etree.fromstring(fzp_xml)
        checker = FZPDateFormatChecker(fzp_doc)
        errors, warnings = checker.check()

        self.assertEqual(errors, 0, "Valid ISO date should not produce errors")
        self.assertEqual(warnings, 0, "Valid ISO date should not produce warnings")
        self.assertEqual(len(checker.fixes), 0, "Valid ISO date should not need fixes")

        # Date should remain unchanged
        date_element = fzp_doc.find('.//date')
        self.assertEqual(date_element.text, "2024-06-13")

    def test_date_format_common_format_check(self):
        """Test that common date format 'Thu Jun 13 2024' is detected by check method"""
        fzp_xml = """<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>Thu Jun 13 2024</date>
</module>"""

        from .fzp_checkers import FZPDateFormatChecker

        fzp_doc = etree.fromstring(fzp_xml)
        checker = FZPDateFormatChecker(fzp_doc)
        errors, warnings = checker.check()

        self.assertEqual(errors, 0, "Fixable date should not produce errors")
        self.assertEqual(warnings, 1, "Fixable date should produce one warning")
        self.assertEqual(len(checker.fixes), 0, "Check method should not apply fixes")

        # Date should remain unchanged after check
        date_element = fzp_doc.find('.//date')
        self.assertEqual(date_element.text, "Thu Jun 13 2024", "Date should be unchanged by check method")

        # Check warning message
        self.assertIn("2024-06-13", checker.issues[0].message)

    def test_date_format_fix_method(self):
        """Test that fix method properly converts date format"""
        import tempfile
        fzp_content = """<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>Thu Jun 13 2024</date>
</module>"""

        from .fzp_checkers import FZPDateFormatChecker

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fzp', delete=False) as temp_file:
            temp_file.write(fzp_content)
            temp_filename = temp_file.name

        try:
            # Parse and check
            fzp_doc = etree.fromstring(fzp_content)
            checker = FZPDateFormatChecker(fzp_doc)

            # Apply fixes
            fixes = checker.fix(temp_filename)

            # Read the modified file
            with open(temp_filename, 'r') as f:
                modified_content = f.read()

            # Check that the date was converted
            self.assertIn("2024-06-13", modified_content)
            self.assertNotIn("Thu Jun 13 2024", modified_content)

            # Check fix results
            self.assertEqual(len(fixes), 1, "Should have applied one fix")
            self.assertIn("Thu Jun 13 2024", fixes[0].message)
            self.assertIn("2024-06-13", fixes[0].message)

        finally:
            # Clean up
            os.unlink(temp_filename)

    def test_date_format_japanese_format(self):
        """Test Japanese date format conversion"""
        fzp_xml = """<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>木 3 31 2016</date>
</module>"""

        from .fzp_checkers import FZPDateFormatChecker

        fzp_doc = etree.fromstring(fzp_xml)
        checker = FZPDateFormatChecker(fzp_doc)
        errors, warnings = checker.check()

        self.assertEqual(errors, 0, "Japanese date should be fixable")
        self.assertEqual(warnings, 1, "Should produce one warning for fixable date")
        self.assertEqual(len(checker.fixes), 0, "Check method should not apply fixes")

        # Date should remain unchanged after check
        date_element = fzp_doc.find('.//date')
        self.assertEqual(date_element.text, "木 3 31 2016", "Date should remain unchanged by check method")

    def test_date_format_ambiguous_dates(self):
        """Test ambiguous date formats (DD/MM vs MM/DD)"""
        test_cases = [
            ("25/06/2024", "2024-06-25"),  # Clearly DD/MM (25 > 12)
            ("06/25/2024", "2024-06-25"),  # Clearly MM/DD (25 > 12)
            ("05/06/2024", "2024-06-05"),  # Ambiguous, defaults to DD/MM
        ]

        from .fzp_checkers import FZPDateFormatChecker

        for input_date, expected_output in test_cases:
            with self.subTest(input_date=input_date):
                fzp_xml = f"""<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>{input_date}</date>
</module>"""

                fzp_doc = etree.fromstring(fzp_xml)
                checker = FZPDateFormatChecker(fzp_doc)
                errors, warnings = checker.check()

                self.assertEqual(errors, 0, f"Date {input_date} should be fixable")
                self.assertEqual(warnings, 1, f"Date {input_date} should produce one warning")

                # Date should remain unchanged after check
                date_element = fzp_doc.find('.//date')
                self.assertEqual(date_element.text, input_date,
                               f"Date {input_date} should remain unchanged by check method")

    def test_date_format_invalid_dates(self):
        """Test invalid date formats"""
        invalid_dates = [
            "Not a date",
            "32/13/2024",
            "June 32 2024",
            "2024-13-01",
            "",
        ]

        from .fzp_checkers import FZPDateFormatChecker

        for invalid_date in invalid_dates:
            with self.subTest(invalid_date=invalid_date):
                fzp_xml = f"""<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date>{invalid_date}</date>
</module>"""

                fzp_doc = etree.fromstring(fzp_xml)
                checker = FZPDateFormatChecker(fzp_doc)
                errors, warnings = checker.check()

                # Should produce either an error or warning
                total_issues = errors + warnings
                self.assertGreater(total_issues, 0, f"Invalid date '{invalid_date}' should produce issues")

    def test_date_format_empty_date(self):
        """Test empty date element"""
        fzp_xml = """<?xml version="1.0"?>
<module fritzingVersion="1.0.0" moduleId="test">
    <version>1.0</version>
    <date></date>
</module>"""

        from .fzp_checkers import FZPDateFormatChecker

        fzp_doc = etree.fromstring(fzp_xml)
        checker = FZPDateFormatChecker(fzp_doc)
        errors, warnings = checker.check()

        self.assertEqual(warnings, 1, "Empty date should produce one warning")
        self.assertIn("empty", checker.issues[0].message.lower())

    def test_date_format_checker_name_and_description(self):
        """Test checker metadata"""
        from .fzp_checkers import FZPDateFormatChecker

        self.assertEqual(FZPDateFormatChecker.get_name(), "date_format")
        self.assertIn("date format", FZPDateFormatChecker.get_description().lower())
        self.assertIn("ISO format", FZPDateFormatChecker.get_description())

    def test_connector_numbering_valid(self):
        self.run_checker('connector_numbering_valid.fzp.test',
                        ['connector_numbering'],
                        [],
                        0,
                        None)

    def test_connector_numbering_invalid(self):
        self.run_checker('connector_numbering_invalid.fzp.test',
                        ['connector_numbering'],
                        [],
                        0,
                        None,
                        3)   # 3 warnings for mismatched connector numbering

    def test_copper_color_valid_standard(self):
        self.run_checker('copper_color_valid_standard.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_valid_uppercase(self):
        self.run_checker('copper_color_valid_uppercase.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_valid_legacy(self):
        self.run_checker('copper_color_valid_legacy.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_valid_inherited(self):
        self.run_checker('copper_color_valid_inherited.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_valid_none(self):
        self.run_checker('copper_color_valid_none.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_valid_nested_copper(self):
        self.run_checker('copper_color_valid_nested_copper.fzp.test',
                        [],
                        ['copper_layer_content'],
                        0,
                        None)

    def test_copper_color_invalid_silkscreen_nested(self):
        self.run_checker('copper_color_invalid_silkscreen_nested.fzp.test',
                        [],
                        ['copper_layer_content'],
                        2,
                        None)

    def test_copper_color_invalid_wrong_color(self):
        self.run_checker('copper_color_invalid_wrong_color.fzp.test',
                        [],
                        ['copper_layer_content'],
                        1,
                        None)

    def test_copper_color_invalid_white_stroke(self):
        self.run_checker('copper_color_invalid_white_stroke.fzp.test',
                        [],
                        ['copper_layer_content'],
                        1,
                        None)

    def test_copper_color_invalid_mixed(self):
        self.run_checker('copper_color_invalid_mixed.fzp.test',
                        [],
                        ['copper_layer_content'],
                        2,
                        None)

    def test_copper_color_invalid_style_attr(self):
        self.run_checker('copper_color_invalid_style_attr.fzp.test',
                        [],
                        ['copper_layer_content'],
                        1,
                        None)

    def test_no_layer_valid(self):
        """Test that SVG with elements inside proper layer group passes."""
        self.run_checker('no_layer_valid.fzp.test',
                        [],
                        ['no_layer'],
                        0,
                        None)

    def test_no_layer_with_namedview(self):
        """Test that sodipodi:namedview elements are correctly skipped"""
        self.run_checker('no_layer_namedview.fzp.test',
                        [],
                        ['no_layer'],
                        0,
                        None)

    def test_no_layer_invalid(self):
        """Test that SVG with elements outside any layer group is detected"""
        self.run_checker('no_layer_invalid.fzp.test',
                        [],
                        ['no_layer'],
                        1,
                        None)

    def test_template_svgs_not_reported_missing(self):
        """Test that template SVGs (generic_ic_*, dip_*, etc.) are not reported as missing"""
        self.run_checker('template_svgs.fzp.test',
                        [],
                        [],
                        0,
                        None)

if __name__ == '__main__':
    unittest.main()
