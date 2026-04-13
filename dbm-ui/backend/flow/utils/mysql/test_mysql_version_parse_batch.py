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

from backend.flow.utils.mysql.mysql_version_parse import (
    ONLINE_MYSQL_VERSION_DRS_CHUNK_SIZE,
    get_online_mysql_versions_batch,
)


class TestGetOnlineMysqlVersionsBatch(SimpleTestCase):
    """get_online_mysql_versions_batch 分片与 DRS 解析"""

    def test_empty_addresses(self):
        self.assertEqual(get_online_mysql_versions_batch([], 0), {})

    @patch("backend.flow.utils.mysql.mysql_version_parse.DRSApi.short_rpc")
    def test_single_chunk(self, mock_rpc):
        mock_rpc.return_value = [
            {
                "address": "127.0.0.1:4306",
                "error_msg": "",
                "cmd_results": [{"table_data": [{"version": "tdbctl-2.4.10"}]}],
            }
        ]
        result = get_online_mysql_versions_batch(["127.0.0.1:4306"], 0)
        self.assertEqual(result["127.0.0.1:4306"], "tdbctl-2.4.10")
        mock_rpc.assert_called_once()
        body = mock_rpc.call_args[0][0]
        self.assertEqual(body["bk_cloud_id"], 0)
        self.assertEqual(body["addresses"], ["127.0.0.1:4306"])

    @patch("backend.flow.utils.mysql.mysql_version_parse.DRSApi.short_rpc")
    def test_serial_two_chunks_for_25_addresses(self, mock_rpc):
        def side_effect(body):
            return [
                {
                    "address": addr,
                    "error_msg": "",
                    "cmd_results": [{"table_data": [{"version": "8.0.0-tdbctl-2.4.1"}]}],
                }
                for addr in body["addresses"]
            ]

        mock_rpc.side_effect = side_effect
        addresses = ["127.0.0.1:{}".format(4300 + i) for i in range(25)]
        result = get_online_mysql_versions_batch(addresses, 3, chunk_size=ONLINE_MYSQL_VERSION_DRS_CHUNK_SIZE)
        self.assertEqual(len(result), 25)
        self.assertEqual(mock_rpc.call_count, 2)
        first_body = mock_rpc.call_args_list[0][0][0]
        second_body = mock_rpc.call_args_list[1][0][0]
        self.assertEqual(len(first_body["addresses"]), 20)
        self.assertEqual(len(second_body["addresses"]), 5)
        self.assertEqual(first_body["bk_cloud_id"], 3)
