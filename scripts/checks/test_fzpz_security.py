#!/usr/bin/env python3
"""
Unit tests for FZPZ security checks in fzp_utils.py
"""
import unittest
import os
import tempfile
import zipfile

from fzp_utils import FZPUtils


class TestFZPZSecurity(unittest.TestCase):
    """Test security features of FZPZ file extraction."""

    def create_malicious_fzpz(self, filename, malicious_path):
        """Create a test fzpz file with a malicious path."""
        with zipfile.ZipFile(filename, 'w') as zf:
            # Add a legitimate FZP file
            zf.writestr('test.fzp', '<?xml version="1.0" encoding="UTF-8"?><module/>')
            # Add a malicious file
            zf.writestr(malicious_path, 'malicious content')

    def test_directory_traversal_attack(self):
        """Test that directory traversal attacks are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "traversal.fzpz")
            self.create_malicious_fzpz(fzpz_file, "../../../etc/passwd")
            
            with self.assertRaises(ValueError) as context:
                FZPUtils.extract_fzpz(fzpz_file)
            
            self.assertIn("Security violation", str(context.exception))
            self.assertIn("Directory traversal", str(context.exception))

    def test_absolute_path_attack(self):
        """Test that absolute paths are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "absolute.fzpz")
            self.create_malicious_fzpz(fzpz_file, "/etc/passwd")
            
            with self.assertRaises(ValueError) as context:
                FZPUtils.extract_fzpz(fzpz_file)
            
            self.assertIn("Security violation", str(context.exception))
            self.assertIn("Absolute path", str(context.exception))

    def test_normalized_path_escape(self):
        """Test that normalized path escapes are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "escape.fzpz")
            self.create_malicious_fzpz(fzpz_file, "normal/../../../evil.txt")
            
            with self.assertRaises(ValueError) as context:
                FZPUtils.extract_fzpz(fzpz_file)
            
            self.assertIn("Security violation", str(context.exception))
            self.assertIn("Directory traversal", str(context.exception))

    def test_windows_style_traversal(self):
        """Test that Windows-style directory traversal is blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "windows.fzpz")
            self.create_malicious_fzpz(fzpz_file, "..\\..\\windows\\system32\\evil.exe")
            
            with self.assertRaises(ValueError) as context:
                FZPUtils.extract_fzpz(fzpz_file)
            
            self.assertIn("Security violation", str(context.exception))
            self.assertIn("Directory traversal", str(context.exception))

    def test_legitimate_fzpz_allowed(self):
        """Test that legitimate FZPZ files are allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "legit.fzpz")
            with zipfile.ZipFile(fzpz_file, 'w') as zf:
                zf.writestr('test.fzp', '<?xml version="1.0" encoding="UTF-8"?><module/>')
                zf.writestr('breadboard.svg', '<svg/>')
                zf.writestr('subfolder/icon.svg', '<svg/>')  # Subdirectories should be allowed
            
            # This should not raise an exception
            result = FZPUtils.extract_fzpz(fzpz_file)
            
            # Verify we got a valid result
            self.assertTrue(result.endswith('test.fzp'))
            self.assertTrue(os.path.exists(result))
            
            # Clean up
            FZPUtils.cleanup_extraction(os.path.dirname(result))

    def test_multiple_violations_reported(self):
        """Test that multiple security violations are reported together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fzpz_file = os.path.join(temp_dir, "multiple.fzpz")
            with zipfile.ZipFile(fzpz_file, 'w') as zf:
                zf.writestr('test.fzp', '<?xml version="1.0" encoding="UTF-8"?><module/>')
                zf.writestr('../../../etc/passwd', 'evil')
                zf.writestr('/etc/shadow', 'more evil')
            
            with self.assertRaises(ValueError) as context:
                FZPUtils.extract_fzpz(fzpz_file)
            
            error_msg = str(context.exception)
            self.assertIn("Security violation", error_msg)
            # Should contain both violations
            self.assertIn("Directory traversal", error_msg)
            self.assertIn("Absolute path", error_msg)


if __name__ == '__main__':
    unittest.main()