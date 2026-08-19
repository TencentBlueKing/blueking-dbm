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

from django.test import TestCase

from backend.db_meta.api.cluster.mysqldts.decommission import decommission
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, LogicalCity, Machine, MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

TEST_BK_CLOUD_ID = 0
TEST_CLUSTER_NAME = "dts-make-test-01"
TEST_MASTER_ADDR = f"{cc.NORMAL_IP}:{MYSQL_DTS_MASTER_PORT}"
TEST_DEPLOY_PATH = f"/data/dts/{TEST_CLUSTER_NAME}"


class MysqlDtsDecommissionTest(TestCase):
    def setUp(self):
        logical, _ = LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        self.bk_city, _ = BKCity.objects.get_or_create(
            bk_idc_city_id=1,
            defaults={"logical_city": logical, "bk_idc_city_name": "南京"},
        )

    def _create_dts(self, name=TEST_CLUSTER_NAME):
        Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MYSQL_DTS_MASTER.value,
            bk_city=self.bk_city,
            access_layer=AccessLayer.PROXY.value,
            bk_host_id=100001,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.MySQLDTS.value,
        )
        Machine.objects.create(
            ip=cc.NORMAL_IP2,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MYSQL_DTS_WORKER.value,
            bk_city=self.bk_city,
            access_layer=AccessLayer.STORAGE.value,
            bk_host_id=100002,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.MySQLDTS.value,
        )
        return MysqlDtsCluster.objects.create(
            name=name,
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_id=0,
            status=MysqlDtsClusterStatus.RUNNING.value,
            master_nodes=[{"ip": cc.NORMAL_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_MASTER_PORT}],
            worker_nodes=[{"ip": cc.NORMAL_IP2, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            master_addr=TEST_MASTER_ADDR,
            deploy_path=TEST_DEPLOY_PATH,
        )

    @patch("backend.db_meta.api.cluster.mysqldts.decommission.CcManage")
    def test_decommission_recycles_machines(self, mock_cc_manage):
        mock_cc_manage.return_value = MagicMock()
        dts = self._create_dts()

        decommission(dts_cluster_id=dts.id, recycle_hosts=True, updater="tester")

        dts.refresh_from_db()
        self.assertEqual(dts.status, MysqlDtsClusterStatus.DESTROYED.value)
        self.assertEqual(dts.cluster_id, 0)
        self.assertFalse(Machine.objects.filter(bk_host_id=100001).exists())
        self.assertFalse(Machine.objects.filter(bk_host_id=100002).exists())

    @patch("backend.db_meta.api.cluster.mysqldts.decommission.CcManage")
    def test_recycle_hosts_true_calls_recycle_host(self, mock_cc_manage):
        cc_inst = MagicMock()
        mock_cc_manage.return_value = cc_inst
        dts = self._create_dts()

        decommission(dts_cluster_id=dts.id, recycle_hosts=True, updater="tester")

        recycled = []
        for call in cc_inst.recycle_host.call_args_list:
            args, kwargs = call
            host_ids = kwargs.get("bk_host_ids") if "bk_host_ids" in kwargs else (args[0] if args else [])
            recycled.extend(host_ids if isinstance(host_ids, list) else [host_ids])
        self.assertEqual(set(recycled), {100001, 100002})
        self.assertEqual(cc_inst.recycle_host.call_count, 2)

    @patch("backend.db_meta.api.cluster.mysqldts.decommission.CcManage")
    def test_recycle_hosts_false_skips_recycle_host(self, mock_cc_manage):
        cc_inst = MagicMock()
        mock_cc_manage.return_value = cc_inst
        dts = self._create_dts(name=f"{TEST_CLUSTER_NAME}-keep")

        decommission(dts_cluster_id=dts.id, recycle_hosts=False, updater="tester")

        cc_inst.recycle_host.assert_not_called()
        self.assertFalse(Machine.objects.filter(bk_host_id=100001).exists())
        self.assertFalse(Machine.objects.filter(bk_host_id=100002).exists())
