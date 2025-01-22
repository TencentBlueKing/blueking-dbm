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

from backend.db_meta.models import Cluster, Machine, ProxyInstance
from backend.tests.mock_data.ticket.mongodb_flow import (
    MONGODB_ADD_MONGOS_TICKET_DATA,
    MONGODB_CLUSTER_DATA,
    MONGODB_CUTOFF_TICKET_DATA,
    MONGODB_DESTROY_TICKET_DATA,
    MONGODB_MACHINE_DATA,
    MONGODB_PROXYINSTANCE_DATA,
    MONGODB_REDUCE_MONGOS_DATA,
    MONGODB_REMOVE_NS_TICKET_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_mongodb_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        Cluster.objects.create(**MONGODB_CLUSTER_DATA)
        Machine.objects.bulk_create([Machine(**data) for data in MONGODB_MACHINE_DATA])
        ProxyInstance.objects.bulk_create([ProxyInstance(**data) for data in MONGODB_PROXYINSTANCE_DATA])
        cluster_id = Cluster.objects.first()
        for proxy_instance in ProxyInstance.objects.all():
            proxy_instance.cluster.add(cluster_id)
        yield
        ProxyInstance.objects.all().delete()
        Cluster.objects.all().delete()
        Machine.objects.all().delete()


class TestMangodbFlow(BaseTicketTest):
    """
    mongodb测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    # mongos 扩容接入层
    def test_add_mongos_flow(self):
        # MONGODB 扩容接入层: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
        self.flow_test(MONGODB_ADD_MONGOS_TICKET_DATA)

    def test_reduce_mongos_flow(self):
        # MONGOS 缩容接入层: start --> itsm --> PAUSE --> INNER_FLOW --> end
        self.flow_test(MONGODB_REDUCE_MONGOS_DATA)

    def test_mongodb_destroy_flow(self):
        # MONGODB 集群下架: start --> itsm --> PAUSE --> INNER_FLOW --> end
        self.flow_test(MONGODB_DESTROY_TICKET_DATA)

    def test_mongo_cutoff_flow(self):
        # MONGODB 整机替换: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
        self.flow_test(MONGODB_CUTOFF_TICKET_DATA)

    def test_mongo_remove_ns(self):
        # start --> itsm --> PAUSE --> INNER_FLOW --> end
        self.flow_test(MONGODB_REMOVE_NS_TICKET_DATA)
