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
import pytest
from mock.mock import patch

from backend.db_meta.api.cluster.mysqldts.create_cluster import append_worker_nodes, create
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, Machine, MysqlDtsCluster, ProxyInstance, StorageInstance
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

TEST_BK_CLOUD_ID = 0
TEST_CLUSTER_NAME = "dts-make-test-01"
TEST_MASTER_ADDR = f"{cc.NORMAL_IP}:{MYSQL_DTS_MASTER_PORT}"
TEST_DEPLOY_PATH = f"/data/dts/{TEST_CLUSTER_NAME}"


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


class TestMysqlDtsCreate:
    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_only_writes_dts_cluster_and_machine(self):
        dts = create(**_create_kwargs())

        assert dts.cluster_id == 0
        assert dts.status == MysqlDtsClusterStatus.RUNNING.value
        assert MysqlDtsCluster.objects.filter(id=dts.id).exists()
        assert Machine.objects.filter(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID).exists()
        assert Machine.objects.filter(ip=cc.NORMAL_IP2, bk_cloud_id=TEST_BK_CLOUD_ID).exists()

        assert not Cluster.objects.filter(cluster_type=ClusterType.MySQLDTS.value, name=TEST_CLUSTER_NAME).exists()
        assert not ProxyInstance.objects.filter(machine__ip=cc.NORMAL_IP, port=MYSQL_DTS_MASTER_PORT).exists()
        assert not StorageInstance.objects.filter(machine__ip=cc.NORMAL_IP2, port=MYSQL_DTS_WORKER_PORT).exists()
        assert not ClusterEntry.objects.filter(entry=TEST_MASTER_ADDR).exists()

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_rejects_duplicate_active_name(self):
        create(**_create_kwargs())
        with pytest.raises(DBMetaException):
            create(**_create_kwargs())

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_create_allows_same_name_after_destroyed(self):
        first = create(**_create_kwargs())
        first.status = MysqlDtsClusterStatus.DESTROYED.value
        first.save(update_fields=["status"])

        second = create(**_create_kwargs())
        assert second.id != first.id
        assert second.cluster_id == 0
        assert MysqlDtsCluster.objects.filter(name=TEST_CLUSTER_NAME).count() == 2

    @patch("backend.db_meta.api.machine.apis.CCApi", cc.CCApiMock())
    def test_append_worker_nodes_updates_json_and_machine(self):
        dts = create(**_create_kwargs(worker_nodes=[]))
        append_worker_nodes(
            dts_cluster_id=dts.id,
            new_worker_nodes=[{"ip": cc.NORMAL_IP2, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            updater="tester",
        )
        dts.refresh_from_db()
        assert len(dts.worker_nodes) == 1
        assert dts.worker_nodes[0]["ip"] == cc.NORMAL_IP2
        worker = Machine.objects.get(ip=cc.NORMAL_IP2, bk_cloud_id=TEST_BK_CLOUD_ID)
        assert worker.machine_type in (
            MachineType.MYSQL_DTS_WORKER.value,
            MachineType.MYSQL_DTS_COLOCATED.value,
        )
        assert not StorageInstance.objects.filter(machine=worker).exists()
