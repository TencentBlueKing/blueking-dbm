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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl import (
    _batch_check_tdbctl_is_primary,
    _filter_upgrade_instances,
)


class TestBatchCheckTdbctlIsPrimary(SimpleTestCase):
    """_batch_check_tdbctl_is_primary 分片与结果解析"""

    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.DRSApi.short_rpc")
    def test_primary_true(self, mock_rpc):
        mock_rpc.return_value = [
            {
                "address": "127.0.0.1:4306",
                "error_msg": "",
                "cmd_results": [{"table_data": [{"IS_THIS_SERVER": "1"}]}],
            }
        ]
        result = _batch_check_tdbctl_is_primary(["127.0.0.1:4306"], 0)
        self.assertTrue(result["127.0.0.1:4306"])

    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.DRSApi.short_rpc")
    def test_chunk_failure_marks_false(self, mock_rpc):
        mock_rpc.side_effect = RuntimeError("network")
        result = _batch_check_tdbctl_is_primary(["127.0.0.1:4306", "127.0.0.2:4306"], 0)
        self.assertFalse(result["127.0.0.1:4306"])
        self.assertFalse(result["127.0.0.2:4306"])


class TestFilterUpgradeInstances(SimpleTestCase):
    """_filter_upgrade_instances 与批量版本、批量 primary 的衔接"""

    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl._batch_check_tdbctl_is_primary")
    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.get_online_mysql_versions_batch")
    @patch("backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl.Package.objects.get")
    def test_upgrade_master_and_skip_newer(self, mock_pkg_get, mock_ver_batch, mock_pri_batch):
        mock_pkg = MagicMock()
        mock_pkg.name = "tdbctl-2.4.12"
        mock_pkg_get.return_value = mock_pkg
        mock_ver_batch.return_value = {
            "127.0.0.1:4306": "tdbctl-2.4.10",
            "127.0.0.2:4306": "tdbctl-2.4.13",
        }
        mock_pri_batch.return_value = {"127.0.0.1:4306": True}
        instances = [
            {"ip": "127.0.0.1", "port": 4306, "spider_port": 3306},
            {"ip": "127.0.0.2", "port": 4306, "spider_port": 3306},
        ]
        slave_list, master_list, target_version, skipped, skipped_versions = _filter_upgrade_instances(
            instances, pkg_id=1, bk_cloud_id=0
        )
        self.assertEqual(target_version, "tdbctl-2.4.12")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["ip"], "127.0.0.2")
        self.assertEqual(len(master_list), 1)
        self.assertEqual(master_list[0]["ip"], "127.0.0.1")
        self.assertEqual(master_list[0]["current_version"], "tdbctl-2.4.10")
        self.assertTrue(master_list[0]["is_primary"])
        self.assertEqual(len(slave_list), 0)
