# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.client import MySQLDTSApi
from backend.components.mysqldtsapi.types import (
    CreateSourceRequest,
    GetSourceResponse,
    PurgeConfig,
    RelayConfig,
    Source,
    SourceDumpFrom,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.register_source import _require_dump_from_echo
from backend.flow.utils.mysql.dts.migrate_helper import build_create_source_request, task_mode_runs_incremental
from backend.flow.utils.mysql.dts.migrate_plan import SourceSpec, SyncScope


class TaskModeRunsIncrementalTest(SimpleTestCase):
    def test_full_is_not_incremental(self):
        self.assertFalse(task_mode_runs_incremental("full"))
        self.assertFalse(task_mode_runs_incremental("FULL"))

    def test_all_incremental_empty_are_incremental(self):
        self.assertTrue(task_mode_runs_incremental("all"))
        self.assertTrue(task_mode_runs_incremental("incremental"))
        self.assertTrue(task_mode_runs_incremental(""))
        self.assertTrue(task_mode_runs_incremental(None))


class BuildCreateSourceRelayTest(SimpleTestCase):
    def _cluster(self):
        cluster = MagicMock()
        cluster.id = 1
        cluster.cluster_type = "tendbha"
        return cluster

    def _src(self):
        return SourceSpec(cluster_id=1, source_name="src-1", sync_scope=SyncScope())

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=None)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_all_enables_relay_and_default_purge(self, _ep, _dump, _gtid):
        req = build_create_source_request(self._src(), self._cluster(), user="u", password="p", task_mode="all")
        self.assertIsNotNone(req.source.relay_config)
        self.assertTrue(req.source.relay_config.enable_relay)
        self.assertEqual(req.source.purge.interval, 600)
        self.assertEqual(req.source.purge.expires, 6)
        self.assertEqual(req.source.purge.remain_space, 50)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=None)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_incremental_enables_relay(self, _ep, _dump, _gtid):
        req = build_create_source_request(
            self._src(), self._cluster(), user="u", password="p", task_mode="incremental"
        )
        self.assertTrue(req.source.relay_config.enable_relay)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=None)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_full_does_not_enable_relay(self, _ep, _dump, _gtid):
        req = build_create_source_request(self._src(), self._cluster(), user="u", password="p", task_mode="full")
        self.assertTrue(req.source.relay_config is None or req.source.relay_config.enable_relay is False)
        self.assertEqual(req.source.purge.interval, 600)
        self.assertEqual(req.source.purge.expires, 6)
        self.assertEqual(req.source.purge.remain_space, 50)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=None)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_default_task_mode_enables_relay(self, _ep, _dump, _gtid):
        req = build_create_source_request(self._src(), self._cluster(), user="u", password="p")
        self.assertTrue(req.source.relay_config.enable_relay)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=("127.0.0.3", 3306))
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_slave_export_is_dump_from_object(self, _ep, _dump, _gtid):
        req = build_create_source_request(self._src(), self._cluster(), user="u", password="p")
        self.assertEqual(req.source.host, "127.0.0.2")
        self.assertEqual(req.source.dump_from.host, "127.0.0.3")
        self.assertEqual(req.source.dump_from.port, 3306)
        self.assertEqual(req.source.dump_from.user, "u")
        self.assertEqual(req.source.dump_from.password, "p")
        dumped = MySQLDTSApi._dump_create_source(req)
        self.assertEqual(
            dumped["source"]["dump_from"],
            {"host": "127.0.0.3", "port": 3306, "user": "u", "password": "p"},
        )
        self.assertNotIn("dump_host", dumped["source"])
        self.assertNotIn("dump_port", dumped["source"])

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=False)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_dump_endpoint", return_value=("127.0.0.2", 3306))
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.2", 3306))
    def test_same_address_omits_dump_from(self, _ep, _dump, _gtid):
        req = build_create_source_request(self._src(), self._cluster(), user="u", password="p")
        self.assertIsNone(req.source.dump_from)
        dumped = MySQLDTSApi._dump_create_source(req)
        self.assertNotIn("dump_from", dumped["source"])


class DumpCreateSourceRelayTest(SimpleTestCase):
    def _request(self, *, enable_relay: bool) -> CreateSourceRequest:
        return CreateSourceRequest(
            source=Source(
                source_name="s1",
                host="127.0.0.2",
                port=3306,
                user="u",
                password="p",
                enable_gtid=False,
                enable=True,
                relay_config=RelayConfig(enable_relay=enable_relay),
            ),
            worker_name="w1",
        )

    def test_dump_omits_default_relay_dir_and_purge(self):
        dumped = MySQLDTSApi._dump_create_source(self._request(enable_relay=True))
        relay = dumped["source"]["relay_config"]
        self.assertEqual(relay.get("enable_relay"), True)
        self.assertNotIn("relay_dir", relay)
        self.assertNotEqual(relay.get("relay_dir"), "./relay_log")
        self.assertNotIn("purge", dumped["source"])
        self.assertFalse(relay.get("relay_binlog_name"))
        self.assertFalse(relay.get("relay_binlog_gtid"))


class DumpFromEchoTest(SimpleTestCase):
    def test_response_keeps_dump_from(self):
        want = SourceDumpFrom(host="127.0.0.3", port=3306, user="u", password="p")
        got = GetSourceResponse(
            source_name="s1",
            host="127.0.0.2",
            port=3306,
            user="u",
            enable_gtid=False,
            enable=True,
            dump_from={"host": "127.0.0.3", "port": 3306, "user": "u"},
        )
        _require_dump_from_echo(want, got.dump_from)

    def test_missing_dump_from_fails(self):
        want = SourceDumpFrom(host="127.0.0.3", port=3306, user="u", password="p")
        with self.assertRaises(ValueError) as ctx:
            _require_dump_from_echo(want, None)
        self.assertIn("127.0.0.3:3306", str(ctx.exception))


class GetSourceResponseRelayNullTest(SimpleTestCase):
    """DTS 刚创建的 Source 会把 relay binlog 字段写成 JSON null。"""

    def test_create_source_response_accepts_null_relay_binlog_fields(self):
        resp = GetSourceResponse(
            source_name="source-322-8458fdcdc2d9",
            host="127.0.0.2",
            port=20000,
            user="dts_u",
            enable_gtid=False,
            enable=True,
            cluster_type="mysql",
            relay_config={
                "enable_relay": True,
                "relay_binlog_name": None,
                "relay_binlog_gtid": None,
                "relay_dir": None,
            },
        )
        self.assertEqual(resp.source_name, "source-322-8458fdcdc2d9")
        self.assertTrue(resp.relay_config.enable_relay)
        self.assertFalse(resp.relay_config.relay_binlog_name)
        self.assertFalse(resp.relay_config.relay_binlog_gtid)

    def test_create_source_response_accepts_null_password_and_purge_ints(self):
        resp = GetSourceResponse(
            source_name="source-322-8458fdcdc2d9",
            host="127.0.0.2",
            port=20000,
            user="dts_u",
            password=None,
            enable_gtid=False,
            enable=True,
            cluster_type="mysql",
            purge={
                "interval": None,
                "expires": None,
                "remain_space": None,
            },
        )
        self.assertIsNone(resp.password)
        self.assertIsNone(resp.purge.interval)
        self.assertIsNone(resp.purge.expires)
        self.assertIsNone(resp.purge.remain_space)

    def test_dump_omits_null_password_and_purge_ints(self):
        dumped = MySQLDTSApi._dump_create_source(
            CreateSourceRequest(
                source=Source(
                    source_name="s1",
                    host="127.0.0.2",
                    port=3306,
                    user="u",
                    password=None,
                    enable_gtid=False,
                    enable=True,
                    purge=PurgeConfig(interval=None, expires=None, remain_space=None),
                )
            )
        )
        source = dumped["source"]
        self.assertNotIn("password", source)
        purge = source.get("purge") or {}
        self.assertNotIn("interval", purge)
        self.assertNotIn("expires", purge)
        self.assertNotIn("remain_space", purge)
