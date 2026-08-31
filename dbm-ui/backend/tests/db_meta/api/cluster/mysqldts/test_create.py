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
import copy
from unittest.mock import patch

from django.test import TestCase

from backend.db_meta.api.cluster.mysqldts.create_cluster import append_worker_nodes, create
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType, MachineTypeAccessLayerMap
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import (
    BKCity,
    Cluster,
    ClusterEntry,
    LogicalCity,
    Machine,
    MysqlDtsCluster,
    ProxyInstance,
    StorageInstance,
)
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

TEST_BK_CLOUD_ID = 0
TEST_CLUSTER_NAME = "dts-make-test-01"
TEST_MASTER_ADDR = f"{cc.NORMAL_IP}:{MYSQL_DTS_MASTER_PORT}"
TEST_DEPLOY_PATH = f"/data/dts/{TEST_CLUSTER_NAME}"


def _cc_api_mock_cloud0():
    """CC mock 默认主机 bk_cloud_id=1，与 DTS 用例 cloud=0 对齐。"""
    hosts = copy.deepcopy(cc.MOCK_LIST_HOSTS_WITHOU_BIZ_RETURN)
    for info in hosts["info"]:
        info["bk_cloud_id"] = TEST_BK_CLOUD_ID
    return cc.CCApiMock(list_hosts_without_biz_return=hosts)


def _create_kwargs(**overrides):
    data = {
        "bk_biz_id": constant.BK_BIZ_ID,
        "bk_cloud_id": TEST_BK_CLOUD_ID,
        "name": TEST_CLUSTER_NAME,
        "master_nodes": [{"ip": cc.NORMAL_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_MASTER_PORT}],
        "worker_nodes": [{"ip": cc.NORMAL_IP2, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
        "master_addr": TEST_MASTER_ADDR,
        "deploy_path": TEST_DEPLOY_PATH,
        "creator": "tester",
    }
    data.update(overrides)
    return data


class MysqlDtsCreateTest(TestCase):
    def setUp(self):
        logical, _ = LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        BKCity.objects.get_or_create(
            bk_idc_city_id=cc.REGISTERED_CITY_ID,
            defaults={"logical_city": logical, "bk_idc_city_name": "南京"},
        )

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_only_writes_dts_cluster_and_machine(self):
        dts = create(**_create_kwargs())

        self.assertEqual(dts.cluster_id, 0)
        self.assertEqual(dts.status, MysqlDtsClusterStatus.RUNNING.value)
        self.assertTrue(MysqlDtsCluster.objects.filter(id=dts.id).exists())
        self.assertTrue(Machine.objects.filter(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID).exists())
        self.assertTrue(Machine.objects.filter(ip=cc.NORMAL_IP2, bk_cloud_id=TEST_BK_CLOUD_ID).exists())

        self.assertFalse(
            Cluster.objects.filter(cluster_type=ClusterType.MySQLDTS.value, name=TEST_CLUSTER_NAME).exists()
        )
        self.assertFalse(ProxyInstance.objects.filter(machine__ip=cc.NORMAL_IP, port=MYSQL_DTS_MASTER_PORT).exists())
        self.assertFalse(
            StorageInstance.objects.filter(machine__ip=cc.NORMAL_IP2, port=MYSQL_DTS_WORKER_PORT).exists()
        )
        self.assertFalse(ClusterEntry.objects.filter(entry=TEST_MASTER_ADDR).exists())

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_rejects_duplicate_active_name(self):
        create(**_create_kwargs())
        with self.assertRaises(DBMetaException):
            create(**_create_kwargs())

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_allows_same_name_after_destroyed(self):
        first = create(**_create_kwargs())
        first.status = MysqlDtsClusterStatus.DESTROYED.value
        first.save(update_fields=["status"])

        second = create(**_create_kwargs())
        self.assertNotEqual(second.id, first.id)
        self.assertEqual(second.cluster_id, 0)
        self.assertEqual(MysqlDtsCluster.objects.filter(name=TEST_CLUSTER_NAME).count(), 2)

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_append_worker_nodes_updates_json_and_machine(self):
        dts = create(**_create_kwargs(worker_nodes=[]))
        append_worker_nodes(
            dts_cluster_id=dts.id,
            new_worker_nodes=[{"ip": cc.NORMAL_IP2, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            updater="tester",
        )
        dts.refresh_from_db()
        self.assertEqual(len(dts.worker_nodes), 1)
        self.assertEqual(dts.worker_nodes[0]["ip"], cc.NORMAL_IP2)
        worker = Machine.objects.get(ip=cc.NORMAL_IP2, bk_cloud_id=TEST_BK_CLOUD_ID)
        self.assertIn(
            worker.machine_type,
            (
                MachineType.MYSQL_DTS_WORKER.value,
                MachineType.MYSQL_DTS_COLOCATED.value,
            ),
        )
        self.assertFalse(StorageInstance.objects.filter(machine=worker).exists())

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_machine_typing_fields_complete(self):
        dts = create(**_create_kwargs())
        master = Machine.objects.get(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID)
        worker = Machine.objects.get(ip=cc.NORMAL_IP2, bk_cloud_id=TEST_BK_CLOUD_ID)
        self.assertEqual(master.cluster_type, ClusterType.MySQLDTS.value)
        self.assertEqual(worker.cluster_type, ClusterType.MySQLDTS.value)
        self.assertEqual(master.machine_type, MachineType.MYSQL_DTS_MASTER.value)
        self.assertEqual(worker.machine_type, MachineType.MYSQL_DTS_WORKER.value)
        self.assertEqual(master.access_layer, MachineTypeAccessLayerMap[MachineType.MYSQL_DTS_MASTER].value)
        self.assertEqual(worker.access_layer, MachineTypeAccessLayerMap[MachineType.MYSQL_DTS_WORKER].value)
        self.assertEqual(master.access_layer, AccessLayer.PROXY.value)
        self.assertEqual(worker.access_layer, AccessLayer.STORAGE.value)
        self.assertEqual(ClusterType.cluster_type_to_db_type(ClusterType.MySQLDTS), "mysql")
        self.assertGreater(dts.id, 0)

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_colocated_upgrade_updates_typing(self):
        create(**_create_kwargs(worker_nodes=[]))
        append_worker_nodes(
            dts_cluster_id=MysqlDtsCluster.objects.get(name=TEST_CLUSTER_NAME).id,
            new_worker_nodes=[{"ip": cc.NORMAL_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            updater="tester",
        )
        machine = Machine.objects.get(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID)
        self.assertEqual(machine.machine_type, MachineType.MYSQL_DTS_COLOCATED.value)
        self.assertEqual(machine.cluster_type, ClusterType.MySQLDTS.value)
        self.assertEqual(machine.access_layer, AccessLayer.PROXY.value)
        self.assertEqual(machine.access_layer, MachineTypeAccessLayerMap[MachineType.MYSQL_DTS_COLOCATED].value)
