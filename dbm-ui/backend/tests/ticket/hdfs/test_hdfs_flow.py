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
from backend.db_meta.models import Cluster, Spec
from backend.tests.mock_data.ticket.hdfs_flow import (
    HDFS_APPLY_DATA,
    HDFS_CLUSTER_DATA,
    HDFS_SCALE_UP_DATA,
    HDFS_SPEC_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_hdfs_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        Cluster.objects.create(**HDFS_CLUSTER_DATA)
        Spec.objects.bulk_create([Spec(**data) for data in HDFS_SPEC_DATA])
        yield
        hdfs_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Hdfs)
        Cluster.objects.filter(cluster_type__in=hdfs_cluster_types).delete()
        Spec.objects.filter(spec_cluster_type=DBType.Hdfs).delete()


class TestHdfsFlow(BaseTicketTest):
    """
    hdfs测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    def test_hdfs_apply_flow(self):
        # hdfs集群部署
        self.flow_test(HDFS_APPLY_DATA)

    def test_hdfs_scale_up_flow(self):
        # hdfs扩容
        self.flow_test(HDFS_SCALE_UP_DATA)
