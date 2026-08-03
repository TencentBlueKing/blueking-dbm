# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.check_long_innodb_trx import CheckLongInnoDbTrxService


class MockData:
    def __init__(self, kwargs):
        self.kwargs = kwargs

    def get_one_of_inputs(self, key):
        if key == "kwargs":
            return self.kwargs
        return {}


class TestCheckLongInnoDbTrxService(SimpleTestCase):
    @staticmethod
    def _data():
        return MockData({"bk_cloud_id": 0, "check_instances": ["127.0.0.1:3306"]})

    @patch("backend.flow.plugins.components.collections.mysql.check_long_innodb_trx.DRSApi.short_rpc")
    @patch("backend.flow.plugins.components.collections.mysql.check_long_innodb_trx.DRSApi.rpc")
    def test_command_error_blocks_flow_with_short_rpc(self, mock_rpc, mock_short_rpc):
        response = [
            {
                "address": "127.0.0.1:3306",
                "error_msg": "",
                "cmd_results": [{"error_msg": "query failed", "table_data": []}],
            }
        ]
        mock_rpc.return_value = response
        mock_short_rpc.return_value = response

        result = CheckLongInnoDbTrxService()._execute(self._data(), None)

        self.assertFalse(result)
        mock_short_rpc.assert_called_once()
        mock_rpc.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.check_long_innodb_trx.DRSApi.short_rpc")
    def test_empty_table_data_passes_flow(self, mock_short_rpc):
        mock_short_rpc.return_value = [
            {
                "address": "127.0.0.1:3306",
                "error_msg": "",
                "cmd_results": [{"error_msg": "", "table_data": []}],
            }
        ]

        result = CheckLongInnoDbTrxService()._execute(self._data(), None)

        self.assertTrue(result)

    @patch("backend.flow.plugins.components.collections.mysql.check_long_innodb_trx.DRSApi.short_rpc")
    def test_long_transaction_blocks_flow(self, mock_short_rpc):
        mock_short_rpc.return_value = [
            {
                "address": "127.0.0.1:3306",
                "error_msg": "",
                "cmd_results": [
                    {
                        "error_msg": "",
                        "table_data": [
                            {
                                "trx_state": "RUNNING",
                                "trx_started": "2026-07-23 00:00:00",
                                "trx_mysql_thread_id": 1,
                            }
                        ],
                    }
                ],
            }
        ]

        result = CheckLongInnoDbTrxService()._execute(self._data(), None)

        self.assertFalse(result)
