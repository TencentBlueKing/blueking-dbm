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

from django.test import SimpleTestCase, TestCase

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, Machine
from backend.flow.utils.mysql.dts.cc_standardize import (
    collect_unique_ips,
    dts_cc_set_name,
    resolve_dts_cc_context,
    transfer_dts_hosts_to_cluster_module,
)
from backend.flow.utils.mysql.dts.constants import DTS_CC_MONITOR_PLUGIN_NAME
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc


class DtsCcStandardizePureHelpersTest(SimpleTestCase):
    def test_dts_cc_set_name_matches_template(self):
        self.assertEqual(dts_cc_set_name(), f"db.{DBType.MySQL.value}.{DTS_CC_MONITOR_PLUGIN_NAME}")
        self.assertEqual(dts_cc_set_name(), "db.mysql.dts")

    def test_collect_unique_ips_dedupes_colocated(self):
        master = [{"ip": "127.0.0.2", "port": 18301}]
        worker = [{"ip": "127.0.0.2", "port": 18501}, {"ip": "127.0.0.3", "port": 18501}]
        self.assertEqual(collect_unique_ips(master, worker), ["127.0.0.2", "127.0.0.3"])

    def test_resolve_context_from_nodes(self):
        biz, name, ips = resolve_dts_cc_context(
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_name="dts-foo",
            master_nodes=[{"ip": "127.0.0.2"}],
            worker_nodes=[{"ip": "127.0.0.3"}],
        )
        self.assertEqual(biz, constant.BK_BIZ_ID)
        self.assertEqual(name, "dts-foo")
        self.assertEqual(ips, ["127.0.0.2", "127.0.0.3"])


class DtsCcStandardizeTransferTest(TestCase):
    @patch("backend.flow.utils.mysql.dts.cc_standardize.CcManage")
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_cmdb_module_with_name", return_value=9002)
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_set_with_name", return_value=9001)
    @patch("backend.flow.utils.mysql.dts.cc_standardize.BizSettings.get_exact_hosting_biz", return_value=3)
    def test_transfer_calls_set_module_and_cc(self, mock_hosting, mock_set, mock_module, mock_cc_manage):
        bk_city = BKCity.objects.first()
        Machine.objects.create(
            ip="127.0.0.2",
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MYSQL_DTS_MASTER.value,
            bk_city=bk_city,
            access_layer=AccessLayer.PROXY.value,
            bk_host_id=200001,
            bk_cloud_id=0,
            cluster_type=ClusterType.MySQLDTS.value,
        )
        Machine.objects.create(
            ip="127.0.0.3",
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MYSQL_DTS_WORKER.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE.value,
            bk_host_id=200002,
            bk_cloud_id=0,
            cluster_type=ClusterType.MySQLDTS.value,
        )
        cc_inst = MagicMock()
        mock_cc_manage.return_value = cc_inst

        module_id = transfer_dts_hosts_to_cluster_module(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=0,
            cluster_name="dts-a",
            ips=["127.0.0.2", "127.0.0.3"],
        )
        self.assertEqual(module_id, 9002)
        mock_hosting.assert_called_once_with(constant.BK_BIZ_ID, ClusterType.MySQLDTS.value)
        mock_set.assert_called_once_with(3, "db.mysql.dts")
        mock_module.assert_called_once_with(3, 9001, "dts-a")
        mock_cc_manage.assert_called_once_with(constant.BK_BIZ_ID, ClusterType.MySQLDTS.value)
        cc_inst.transfer_host_module.assert_called_once()
        args, kwargs = cc_inst.transfer_host_module.call_args
        self.assertEqual(set(kwargs.get("bk_host_ids") or args[0]), {200001, 200002})
        self.assertEqual(kwargs.get("target_module_ids") or args[1], [9002])

    @patch("backend.flow.utils.mysql.dts.cc_standardize.CcManage")
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_cmdb_module_with_name", return_value=1)
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_set_with_name", return_value=1)
    @patch("backend.flow.utils.mysql.dts.cc_standardize.BizSettings.get_exact_hosting_biz", return_value=3)
    def test_transfer_propagates_cc_error(self, _h, _s, _m, mock_cc_manage):
        bk_city = BKCity.objects.first()
        Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MYSQL_DTS_MASTER.value,
            bk_city=bk_city,
            access_layer=AccessLayer.PROXY.value,
            bk_host_id=200010,
            bk_cloud_id=0,
            cluster_type=ClusterType.MySQLDTS.value,
        )
        mock_cc_manage.return_value.transfer_host_module.side_effect = RuntimeError("cc fail")
        with self.assertRaisesRegex(RuntimeError, "cc fail"):
            transfer_dts_hosts_to_cluster_module(
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=0,
                cluster_name="dts-err",
                ips=[cc.NORMAL_IP],
            )

    @patch("backend.flow.utils.mysql.dts.cc_standardize.CcManage")
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_cmdb_module_with_name")
    @patch("backend.flow.utils.mysql.dts.cc_standardize.get_or_create_set_with_name", return_value=9001)
    @patch("backend.flow.utils.mysql.dts.cc_standardize.BizSettings.get_exact_hosting_biz", return_value=3)
    def test_two_clusters_share_set_distinct_modules(self, _h, mock_set, mock_module, mock_cc_manage):
        """AE3: 多集群共用 Set，Module 按集群名分开。"""
        bk_city = BKCity.objects.first()
        for ip, host_id in (("127.0.0.2", 200021), ("127.0.0.3", 200022)):
            Machine.objects.create(
                ip=ip,
                bk_biz_id=constant.BK_BIZ_ID,
                machine_type=MachineType.MYSQL_DTS_MASTER.value,
                bk_city=bk_city,
                access_layer=AccessLayer.PROXY.value,
                bk_host_id=host_id,
                bk_cloud_id=0,
                cluster_type=ClusterType.MySQLDTS.value,
            )
        mock_cc_manage.return_value = MagicMock()
        mock_module.side_effect = [9101, 9102]

        transfer_dts_hosts_to_cluster_module(
            bk_biz_id=constant.BK_BIZ_ID, bk_cloud_id=0, cluster_name="dts-a", ips=["127.0.0.2"]
        )
        transfer_dts_hosts_to_cluster_module(
            bk_biz_id=constant.BK_BIZ_ID, bk_cloud_id=0, cluster_name="dts-b", ips=["127.0.0.3"]
        )

        self.assertEqual(mock_set.call_count, 2)
        self.assertTrue(all(c.args == (3, "db.mysql.dts") for c in mock_set.call_args_list))
        self.assertEqual(mock_module.call_args_list[0].args, (3, 9001, "dts-a"))
        self.assertEqual(mock_module.call_args_list[1].args, (3, 9001, "dts-b"))
