import unittest
import os
import sys
from io import StringIO
from fzp_checker_runner import FZPCheckerRunner, AVAILABLE_CHECKERS, SVG_AVAILABLE_CHECKERS

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

    def run_checker(self, fzp_filename, fzp_checkers, svg_checkers, expected_errors, expected_message):
        fzp_file = os.path.join(self.test_data_dir, fzp_filename)
        checker_runner = FZPCheckerRunner(fzp_file, verbose=self.verbose)

             # Run specific FZP and SVG checkers for this test case
        checker_runner.check(fzp_checkers, svg_checkers)

        self.assertEqual(expected_errors, checker_runner.total_errors)

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



if __name__ == '__main__':
    unittest.main()