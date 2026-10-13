# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.drop_user import DropUserService
from backend.flow.utils.mysql.dts.migrate_credentials import build_dts_drop_user_parallel_acts


class DropUserLocalOnlyTest(SimpleTestCase):
    def _execute(self, kwargs, rpc_result):
        service = DropUserService()
        service.log_info = MagicMock()
        service.log_warning = MagicMock()
        service.log_error = MagicMock()
        data = MagicMock()
        data.get_one_of_inputs.return_value = kwargs
        with patch(
            "backend.flow.plugins.components.collections.mysql.drop_user.DRSApi.rpc",
            return_value=rpc_result,
        ) as rpc:
            ok = service._execute(data, parent_data=None)
        payload = rpc.call_args[0][0]
        return ok, payload

    def test_default_drop_is_one_statement(self):
        ok, payload = self._execute(
            {"bk_cloud_id": 0, "host": "127.0.0.3", "user": "dts_u", "address": "127.0.0.1:20000"},
            [{"error_msg": "", "cmd_results": [{"cmd": "drop user", "error_msg": ""}]}],
        )
        self.assertTrue(ok)
        self.assertEqual(payload["cmds"], ["drop user `dts_u`@`127.0.0.3`;"])
        self.assertFalse(payload["force"])

    def test_disable_binlog_wraps_drop(self):
        ok, payload = self._execute(
            {
                "bk_cloud_id": 0,
                "host": "127.0.0.3",
                "user": "dts_u",
                "address": "127.0.0.1:20000",
                "disable_binlog": True,
            },
            [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"cmd": "set session sql_log_bin = 0;", "error_msg": ""},
                        {"cmd": "drop user `dts_u`@`127.0.0.3`;", "error_msg": ""},
                        {"cmd": "set session sql_log_bin = 1;", "error_msg": ""},
                    ],
                }
            ],
        )
        self.assertTrue(ok)
        self.assertTrue(payload["force"])
        self.assertEqual(
            payload["cmds"],
            [
                "set session sql_log_bin = 0;",
                "drop user `dts_u`@`127.0.0.3`;",
                "set session sql_log_bin = 1;",
            ],
        )

    def test_primary_tdbctl_sets_tc_admin(self):
        ok, payload = self._execute(
            {
                "bk_cloud_id": 0,
                "host": "127.0.0.3",
                "user": "dts_u",
                "address": "127.0.0.15:26000",
                "disable_binlog": True,
                "primary_tdbctl": True,
            },
            [{"error_msg": "", "cmd_results": [{"cmd": "drop user", "error_msg": ""}]}],
        )
        self.assertTrue(ok)
        self.assertTrue(payload["force"])
        self.assertEqual(
            payload["cmds"],
            [
                "set session sql_log_bin = 0;",
                "set tc_admin = 0;",
                "drop user `dts_u`@`127.0.0.3`;",
                "set session sql_log_bin = 1;",
            ],
        )

    def test_later_cmd_error_fails_when_not_ignorable(self):
        ok, payload = self._execute(
            {
                "bk_cloud_id": 0,
                "host": "127.0.0.3",
                "user": "dts_u",
                "address": "127.0.0.1:20000",
                "disable_binlog": True,
                "ignore_errors": True,
            },
            [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"cmd": "set session sql_log_bin = 0;", "error_msg": ""},
                        {"cmd": "drop user `dts_u`@`127.0.0.3`;", "error_msg": "Access denied"},
                        {"cmd": "set session sql_log_bin = 1;", "error_msg": ""},
                    ],
                }
            ],
        )
        self.assertFalse(ok)
        self.assertTrue(payload["force"])

    def test_missing_user_on_later_cmd_is_ignored(self):
        ok, payload = self._execute(
            {
                "bk_cloud_id": 0,
                "host": "127.0.0.3",
                "user": "dts_u",
                "address": "127.0.0.1:20000",
                "disable_binlog": True,
                "ignore_errors": True,
            },
            [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"cmd": "set session sql_log_bin = 0;", "error_msg": ""},
                        {
                            "cmd": "drop user `dts_u`@`127.0.0.3`;",
                            "error_msg": "ERROR 1396 (HY000): Operation DROP USER failed",
                        },
                        {"cmd": "set session sql_log_bin = 1;", "error_msg": ""},
                    ],
                }
            ],
        )
        self.assertTrue(ok)
        self.assertTrue(payload["force"])

    def test_dts_drop_acts_disable_binlog(self):
        acts = build_dts_drop_user_parallel_acts(
            dts_user="dts_migrate_abc",
            grant_hosts=["127.0.0.3"],
            grant_targets=[{"bk_cloud_id": 0, "address": "127.0.0.2:20000", "cluster_id": 1}],
            ignore_errors=True,
        )
        self.assertTrue(acts[0]["kwargs"]["disable_binlog"])
        self.assertFalse(acts[0]["kwargs"]["primary_tdbctl"])

    def test_dts_drop_acts_tc_admin_only_on_primary_tdbctl(self):
        acts = build_dts_drop_user_parallel_acts(
            dts_user="dts_migrate_abc",
            grant_hosts=["127.0.0.3"],
            grant_targets=[
                {"bk_cloud_id": 0, "address": "127.0.0.15:25000", "cluster_id": 1, "primary_tdbctl": False},
                {"bk_cloud_id": 0, "address": "127.0.0.15:26000", "cluster_id": 1, "primary_tdbctl": True},
                {"bk_cloud_id": 0, "address": "127.0.0.40:20000", "cluster_id": 1},
            ],
            ignore_errors=True,
        )
        by_addr = {act["kwargs"]["address"]: act["kwargs"]["primary_tdbctl"] for act in acts}
        self.assertFalse(by_addr["127.0.0.15:25000"])
        self.assertTrue(by_addr["127.0.0.15:26000"])
        self.assertFalse(by_addr["127.0.0.40:20000"])
