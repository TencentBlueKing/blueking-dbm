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
import logging
from unittest.mock import patch

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, Spec, StorageInstance, TenDBClusterSpiderExt
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.drs import DRSApiMock
from backend.tests.mock_data.ticket.tendbcluster_flow import (
    TENDBCLUSTER_APPLY_DATA,
    TENDBCLUSTER_CHECKSUM_DATA,
    TENDBCLUSTER_CLUSTER_DATA,
    TENDBCLUSTER_DB_TABLE_BACKUP_DATA,
    TENDBCLUSTER_FULL_BACKUP_DATA,
    TENDBCLUSTER_MACHINE_DATA,
    TENDBCLUSTER_PROXYINSTANCE_DATA,
    TENDBCLUSTER_ROLLBACK_CLUSTER_DATA,
    TENDBCLUSTER_SPEC_DATA,
    TENDBCLUSTER_SPIDER_SLAVE_APPLY_DATA,
    TENDBCLUSTER_SPIDER_SWITCH_NODES_DATA,
    TENDBCLUSTER_SPIDEREXT_DATA,
    TENDBCLUSTER_STORAGE_INSTANCE,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_tendbcluster_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        cluster = Cluster.objects.create(**TENDBCLUSTER_CLUSTER_DATA)
        Machine.objects.bulk_create([Machine(**data) for data in TENDBCLUSTER_MACHINE_DATA])
        storage_instances = StorageInstance.objects.bulk_create(
            [StorageInstance(**data) for data in TENDBCLUSTER_STORAGE_INSTANCE]
        )
        proxy_instances = ProxyInstance.objects.bulk_create(
            [ProxyInstance(**data) for data in TENDBCLUSTER_PROXYINSTANCE_DATA]
        )
        storage_instances[0].cluster.add(cluster)
        proxy_instances[0].cluster.add(cluster)
        proxy_instances[1].cluster.add(cluster)
        proxy_instances[0].storageinstance.add(storage_instances[0])
        proxy_instances[1].storageinstance.add(storage_instances[0])
        Spec.objects.bulk_create([Spec(**data) for data in TENDBCLUSTER_SPEC_DATA])
        TenDBClusterSpiderExt.objects.bulk_create(
            [TenDBClusterSpiderExt(**data) for data in TENDBCLUSTER_SPIDEREXT_DATA]
        )
        yield
        tendbcluster_cluster_types = ClusterType.db_type_to_cluster_types(DBType.TenDBCluster)
        Cluster.objects.filter(cluster_type__in=tendbcluster_cluster_types).delete()
        TenDBClusterSpiderExt.objects.filter(spider_role="spider_master").delete()
        ProxyInstance.objects.filter(cluster_type__in=tendbcluster_cluster_types).delete()
        StorageInstance.objects.filter(cluster_type__in=tendbcluster_cluster_types).delete()
        Machine.objects.filter(cluster_type__in=tendbcluster_cluster_types).delete()
        Spec.objects.filter(spec_cluster_type=DBType.TenDBCluster).delete()


class TestTenDBClusterFlow(BaseTicketTest):
    """
    tendbcluster测试类
    """

    @classmethod
    def apply_patches(cls):
        cls.patches.extend(
            [
                patch("backend.db_services.mysql.remote_service.handlers.DRSApi", DRSApiMock),
                patch("backend.flow.utils.spider.spider_bk_config.DBConfigApi", DBConfigApiMock),
                patch("backend.ticket.builders.tendbcluster.tendb_apply.DBConfigApi", DBConfigApiMock),
            ]
        )
        super().apply_patches()

    def test_tendbcluster_apply_flow(self):
        self.flow_test(TENDBCLUSTER_APPLY_DATA)

    def test_tendbcluster_full_backup_flow(self):
        # tendbcluster全库备份
        self.flow_test(TENDBCLUSTER_FULL_BACKUP_DATA)

    def test_tendbcluster_back_up_flow(self):
        self.flow_test(TENDBCLUSTER_DB_TABLE_BACKUP_DATA)

    def test_tendbcluster_checksum_flow(self):
        self.flow_test(TENDBCLUSTER_CHECKSUM_DATA)

    def test_tendbcluster_rollback_cluster_flow(self):
        self.flow_test(TENDBCLUSTER_ROLLBACK_CLUSTER_DATA)

    def test_tendbcluster_spider_slave_apply_flow(self):
        self.flow_test(TENDBCLUSTER_SPIDER_SLAVE_APPLY_DATA)

    def test_tendbcluster_spider_switch_nodes_flow(self):
        self.flow_test(TENDBCLUSTER_SPIDER_SWITCH_NODES_DATA)
