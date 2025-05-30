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
from backend.db_meta.models import Cluster, Machine, Spec, StorageInstance
from backend.tests.mock_data.ticket.es_flow import (
    ES_APPLY_DATA,
    ES_CLUSTER_DATA,
    ES_DISABLE_DATA,
    ES_MACHINE_DATA,
    ES_SCALE_UP_DATA,
    ES_SHRINK_DATA,
    ES_SPEC_DATA,
    ES_STORAGE_INSTANCE,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_es_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        cluster = Cluster.objects.create(**ES_CLUSTER_DATA)
        Machine.objects.bulk_create([Machine(**data) for data in ES_MACHINE_DATA])
        Spec.objects.bulk_create([Spec(**data) for data in ES_SPEC_DATA])
        storage_instances = StorageInstance.objects.bulk_create(
            [StorageInstance(**data) for data in ES_STORAGE_INSTANCE]
        )
        storage_instances[0].cluster.add(cluster)
        storage_instances[1].cluster.add(cluster)
        yield
        es_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Es)
        Cluster.objects.filter(cluster_type__in=es_cluster_types).delete()
        StorageInstance.objects.filter(cluster_type__in=es_cluster_types).delete()
        Machine.objects.filter(cluster_type__in=es_cluster_types).delete()
        Spec.objects.filter(spec_cluster_type=DBType.Es).delete()


class TestEsFlow(BaseTicketTest):
    """
    es测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    def test_es_apply_flow(self):
        # es集群部署
        self.flow_test(ES_APPLY_DATA)

    def test_es_scale_up_flow(self):
        # es集群扩容
        self.flow_test(ES_SCALE_UP_DATA)

    def test_es_shrink_flow(self):
        # es集群缩容
        self.flow_test(ES_SHRINK_DATA)

    def test_es_disable(self):
        # es禁用
        self.flow_test(ES_DISABLE_DATA)
