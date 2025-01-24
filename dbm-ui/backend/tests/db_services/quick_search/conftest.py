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

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, Cluster, Machine, ProxyInstance, StorageInstance
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

INSTANCE_VERSION = "latest"
INSTANCE_PORT = 8000
INSTANCE_NAME = "zookeeper"
TASK_ROOT_ID = "202304250963aa"


@pytest.fixture
def init_proxy_instance():
    bk_city = BKCity.objects.first()
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
    )
    cluster = Cluster.objects.first()
    proxy_instance = ProxyInstance.objects.create(
        version=INSTANCE_VERSION,
        port=INSTANCE_PORT,
        machine=machine,
        bk_biz_id=constant.BK_BIZ_ID,
        name=INSTANCE_NAME,
        cluster_type=ClusterType.TenDBHA.value,
    )
    proxy_instance.cluster.add(cluster)
    yield proxy_instance


@pytest.fixture
def init_storage_instance():
    bk_city = BKCity.objects.first()
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
    )
    cluster = Cluster.objects.first()
    storage_instance = StorageInstance.objects.create(
        version=INSTANCE_VERSION,
        port=INSTANCE_PORT,
        machine=machine,
        bk_biz_id=constant.BK_BIZ_ID,
        name=INSTANCE_NAME,
        cluster_type=ClusterType.TenDBHA.value,
    )
    storage_instance.cluster.add(cluster)
    yield storage_instance


@pytest.fixture
def init_flow_tree():
    task = FlowTree.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        uid=1,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        root_id=TASK_ROOT_ID,
        tree={},
        status=StateType.FINISHED,
    )
    yield task


@pytest.fixture
def init_ticket():
    ticket = Ticket.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        group=DBType.MySQL,
        remark="",
        details={},
        send_msg_config={},
        is_reviewed=False,
    )
    yield ticket
