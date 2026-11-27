# MIT License — same as dbha-v2 module
"""Unit tests for the scan whitelist API warning in render_configs."""

import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_configs import warn_scan_whitelist_without_api  # noqa: E402

_SWITCH = "ANALYSIS_WORKFLOW_ENABLE_WHITE_LIST_FOR_SCAN"
_API = "COMMON_DBHAV1_API_BLACK_WHITELIST_GET_API"


class TestWarnScanWhitelistWithoutApi(unittest.TestCase):
    def _warned(self, values: dict) -> bool:
        buf = io.StringIO()
        with redirect_stderr(buf):
            warned = warn_scan_whitelist_without_api(values)
        self.assertEqual(warned, bool(buf.getvalue()))
        return warned

    def test_warns_when_enabled_without_api(self) -> None:
        cases = (
            {_SWITCH: "true", _API: ""},
            {_SWITCH: "True", _API: "  "},
            {_SWITCH: "", _API: ""},
            {_API: ""},
        )
        for values in cases:
            with self.subTest(values=values):
                self.assertTrue(self._warned(values))

    def test_silent_when_api_set_or_disabled(self) -> None:
        cases = (
            {_SWITCH: "true", _API: "http://127.0.0.1:8080/blackwhitelist/"},
            {_SWITCH: "false", _API: ""},
            {_SWITCH: "FALSE", _API: ""},
        )
        for values in cases:
            with self.subTest(values=values):
                self.assertFalse(self._warned(values))


if __name__ == "__main__":
    unittest.main()
