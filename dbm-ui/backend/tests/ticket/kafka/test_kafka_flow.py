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
from backend.tests.mock_data.ticket.kafka_flow import (
    KAFKA_APPLY_DATA,
    KAFKA_CLUSTER_DATA,
    KAFKA_DISABLE_DATA,
    KAFKA_SCALE_UP_DATA,
    KAFKA_SPEC_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_kafka_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        Cluster.objects.create(**KAFKA_CLUSTER_DATA)
        Spec.objects.bulk_create([Spec(**data) for data in KAFKA_SPEC_DATA])
        yield
        kafka_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Kafka)
        Cluster.objects.filter(cluster_type__in=kafka_cluster_types).delete()
        Spec.objects.filter(spec_cluster_type=DBType.Kafka).delete()


class TestKafkaFlow(BaseTicketTest):
    """
    kafka测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    def test_kafka_apply_flow(self):
        # kafka集群部署
        self.flow_test(KAFKA_APPLY_DATA)

    def test_kafka_scale_up_flow(self):
        # kafka扩容
        self.flow_test(KAFKA_SCALE_UP_DATA)

    def test_kafka_disable(self):
        # kafka禁用
        self.flow_test(KAFKA_DISABLE_DATA)
