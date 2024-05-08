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

        self.assertEqual(checker_runner.total_errors, expected_errors)

    def test_pcb_only(self):
        self.run_checker('pcb_only.fzp.test',
                         ['missing_tags','connector_terminal','connector_visibility'],
                         ['font_size','viewbox','ids'], 0, None)

    # def test_missing_tags(self):
    #     self.run_checker('missing_tags.fzp.test', ['missing_tags'], [], 1, 'Missing required tag')
    #
    # def test_invalid_terminal(self):
    #     self.run_checker('invalid_terminal.fzp.test', ['connector_terminal'], [], 1, 'references missing terminal')
    #
    # def test_invisible_connector(self):
    #     self.run_checker('invisible_connector.fzp.test', ['connector_visibility'], [], 1, 'Invisible connector')

if __name__ == '__main__':
    unittest.main()