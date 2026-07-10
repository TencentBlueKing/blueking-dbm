# -*- coding: utf-8 -*-
"""verify_helper：OpenAPI addr 解析与节点匹配单测。"""
import os
import sys
import unittest
from types import SimpleNamespace

_DBM_UI = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../"))
if _DBM_UI not in sys.path:
    sys.path.insert(0, _DBM_UI)

from django.conf import settings  # noqa: E402

if not settings.configured:
    # 仅满足 gettext 调用，不拉起完整 Django apps
    settings.configure(USE_I18N=False, SECRET_KEY="test-verify-helper")

from backend.flow.utils.mysql.dts.verify_helper import (  # noqa: E402
    extract_ip_from_addr,
    format_api_nodes,
    match_nodes,
)


class ExtractIpFromAddrTest(unittest.TestCase):
    def test_http_peer_url(self):
        self.assertEqual(extract_ip_from_addr("http://127.0.0.2:18401"), "127.0.0.2")

    def test_host_port_without_scheme(self):
        self.assertEqual(extract_ip_from_addr("127.0.0.3:18301"), "127.0.0.3")

    def test_bare_ip(self):
        self.assertEqual(extract_ip_from_addr("127.0.0.4"), "127.0.0.4")

    def test_empty(self):
        self.assertEqual(extract_ip_from_addr(""), "")


class FormatApiNodesTest(unittest.TestCase):
    def test_master_shows_alive_leader(self):
        items = [SimpleNamespace(name="dm-master-0", addr="http://127.0.0.2:18401", alive=True, leader=True)]
        text = format_api_nodes(items)
        self.assertIn("alive=True", text)
        self.assertIn("leader=True", text)
        self.assertNotIn("bound_stage", text)

    def test_worker_shows_bound_stage_not_alive(self):
        items = [
            SimpleNamespace(
                name="dm-worker-1",
                addr="127.0.0.2:18501",
                bound_stage="free",
                bound_source_name="",
            )
        ]
        text = format_api_nodes(items)
        self.assertIn("bound_stage=free", text)
        self.assertNotIn("alive=", text)


class MatchNodesTest(unittest.TestCase):
    def test_match_http_addr_against_plain_ip(self):
        api_items = [SimpleNamespace(name="dts-master-1", addr="http://127.0.0.2:18401", alive=True, leader=True)]
        expected = [{"ip": "127.0.0.2", "bk_cloud_id": 0}]
        match_nodes(api_items, expected, "Master")

    def test_match_worker_host_port_addr(self):
        api_items = [
            SimpleNamespace(name="dm-worker-1", addr="127.0.0.2:18501", bound_stage="free", bound_source_name="")
        ]
        expected = [{"ip": "127.0.0.2", "name": "dm-worker-1", "port": 18501}]
        match_nodes(api_items, expected, "Worker")

    def test_missing_raises_detailed_error(self):
        api_items = [SimpleNamespace(name="dts-master-1", addr="http://127.0.0.2:18401", alive=True, leader=True)]
        expected = [{"ip": "127.0.0.9", "name": "dm-master-0", "port": 18301}]
        with self.assertRaises(ValueError) as ctx:
            match_nodes(api_items, expected, "Master")
        msg = str(ctx.exception)
        self.assertIn("127.0.0.9", msg)
        self.assertIn("127.0.0.2", msg)
        self.assertIn("dts-master-1@", msg)
        self.assertIn("dm-master-0@127.0.0.9:18301", msg)
        self.assertIn("alive=True", msg)


if __name__ == "__main__":
    unittest.main()
