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

from unittest import TestCase
from unittest.mock import patch

from backend.flow.utils.mysql.dts.precheck.collector import Endpoint, InstanceCollector, PrecheckCollectError


class InstanceCollectorTest(TestCase):
    def setUp(self):
        self.collector = InstanceCollector(Endpoint("127.0.0.1", 3306, 0, 12))

    @patch(
        "backend.flow.utils.mysql.dts.precheck.collector.get_online_mysql_version",
        return_value="5.7.44",
    )
    def test_mysql_version_returns_raw_value(self, get_version):
        self.assertEqual(self.collector.mysql_version(), "5.7.44")
        get_version.assert_called_once_with("127.0.0.1", 3306, 0)

    @patch(
        "backend.flow.utils.mysql.dts.precheck.collector.get_online_mysql_version",
        return_value="",
    )
    def test_empty_mysql_version_is_collection_error(self, _get_version):
        with self.assertRaises(PrecheckCollectError):
            self.collector.mysql_version()

    @patch("backend.flow.utils.mysql.dts.precheck.collector.DRSApi.short_rpc")
    def test_query_extracts_table_data(self, short_rpc):
        short_rpc.return_value = [{"error_msg": "", "cmd_results": [{"error_msg": "", "table_data": [{"v": 1}]}]}]
        self.assertEqual(self.collector.query("SELECT 1"), [{"v": 1}])

    @patch("backend.flow.utils.mysql.dts.precheck.collector.DRSApi.short_rpc")
    def test_query_error_is_collection_error(self, short_rpc):
        short_rpc.return_value = [{"error_msg": "connection refused"}]
        with self.assertRaises(PrecheckCollectError):
            self.collector.query("SELECT 1")

    @patch("backend.flow.utils.mysql.dts.precheck.collector.DRSApi.short_rpc")
    def test_user_schemas_excludes_system_databases(self, short_rpc):
        short_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {
                        "error_msg": "",
                        "table_data": [{"Database": "mysql"}, {"Database": "app"}],
                    }
                ],
            }
        ]
        self.assertEqual(self.collector.user_schemas(), ["app"])
