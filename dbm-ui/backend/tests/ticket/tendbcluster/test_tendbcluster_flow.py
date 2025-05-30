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

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.tests.mock_data.ticket.tendbcluster import TENDBCLUSTER_CLUSTER_DATA, TENDBCLUSTER_FULL_BACKUP_DATA
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_tendbcluster_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        Cluster.objects.create(**TENDBCLUSTER_CLUSTER_DATA)
        yield
        tendbcluster_cluster_types = ClusterType.db_type_to_cluster_types(DBType.TenDBCluster)
        Cluster.objects.filter(cluster_type__in=tendbcluster_cluster_types).delete()


class TestTenDBClusterFlow(BaseTicketTest):
    """
    tendbcluster测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    def test_tendbcluster_full_backup_flow(self):
        # tendbcluster全库备份
        self.flow_test(TENDBCLUSTER_FULL_BACKUP_DATA)
