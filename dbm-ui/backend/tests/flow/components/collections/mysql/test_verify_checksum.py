# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.verify_checksum import VerifyChecksumService


class VerifyChecksumSkipIfNoRecordsTest(SimpleTestCase):
    def _run(self, *, skip_if_no_records: bool, rpc_side_effect):
        service = VerifyChecksumService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        data = MagicMock()
        data.get_one_of_inputs.return_value = {
            "bk_cloud_id": 0,
            "skip_if_no_records": skip_if_no_records,
            "checksum_instance_tuples": [{"master": "127.0.0.1:3306", "slave": "127.0.0.2:3306"}],
        }
        with patch(
            "backend.flow.plugins.components.collections.mysql.verify_checksum.DRSApi.rpc",
            side_effect=rpc_side_effect,
        ):
            return service._execute(data, parent_data=None)

    def test_skip_when_no_records_and_flag_true(self):
        def rpc(payload):
            if len(payload["cmds"]) == 1:
                return [{"error_msg": "", "cmd_results": [{"table_data": [{"t": 0}]}]}]
            return [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"table_data": [{"cnt": 0}], "error_msg": ""},
                        {"table_data": [{"cnt": 0}], "error_msg": ""},
                    ],
                }
            ]

        self.assertTrue(self._run(skip_if_no_records=True, rpc_side_effect=rpc))

    def test_fail_when_no_records_and_flag_false(self):
        def rpc(payload):
            if len(payload["cmds"]) == 1:
                return [{"error_msg": "", "cmd_results": [{"table_data": [{"t": 0}]}]}]
            return [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"table_data": [{"cnt": 0}], "error_msg": ""},
                        {"table_data": [{"cnt": 0}], "error_msg": ""},
                    ],
                }
            ]

        self.assertFalse(self._run(skip_if_no_records=False, rpc_side_effect=rpc))

    def test_fail_on_diff_even_when_skip_flag_true(self):
        def rpc(payload):
            if len(payload["cmds"]) == 1:
                return [{"error_msg": "", "cmd_results": [{"table_data": [{"t": 0}]}]}]
            return [
                {
                    "error_msg": "",
                    "cmd_results": [
                        {"table_data": [{"cnt": 1}], "error_msg": ""},
                        {"table_data": [{"cnt": 1}], "error_msg": ""},
                    ],
                }
            ]

        self.assertFalse(self._run(skip_if_no_records=True, rpc_side_effect=rpc))

    def test_skip_on_drs_error_when_flag_true(self):
        def rpc(payload):
            return [{"error_msg": "connection refused", "cmd_results": []}]

        self.assertTrue(self._run(skip_if_no_records=True, rpc_side_effect=rpc))
