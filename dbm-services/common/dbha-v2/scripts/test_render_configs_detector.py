# MIT License — same as dbha-v2 module
"""Unit tests for probe install directory validation in render_configs."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_configs import validate_probe_install_dir  # noqa: E402


class TestValidateProbeInstallDir(unittest.TestCase):
    def test_valid_paths(self) -> None:
        valid = (
            "/usr/local/dbha-v2",
            "~/.dbha-v2",
            "/home/mysql/dbha-v2",
        )
        for path in valid:
            with self.subTest(path=path):
                validate_probe_install_dir(path)

    def test_invalid_paths(self) -> None:
        invalid = (
            "/tmp/../etc",
            "/path with space",
            "/path$HOME",
            '/path"quote',
        )
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validate_probe_install_dir(path)


if __name__ == "__main__":
    unittest.main()
