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
from unittest import TestCase
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from backend.db_meta.models import Cluster, Machine, Spec, StorageInstance
from backend.db_meta.models.db_module import DBModule
from backend.tests.mock_data.ticket.doris_flow import (
    DORIS_APPLY_TICKET_DATA,
    DORIS_CLUSTER_DATA,
    DORIS_DESTROY_TICKET_DATA,
    DORIS_DISABLE_TICKET_DATA,
    DORIS_ENABLE_TICKET_DATA,
    DORIS_SOURCE_APPLICATION_DATA,
    DORIS_SPEC_DATA,
)
from backend.tests.ticket.server_base import TestFlowBase
from backend.ticket.constants import TicketFlowStatus, TicketStatus

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()

INITIAL_FLOW_FINISHED_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED]
CHANGED_MOCK_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED, TicketFlowStatus.RUNNING]


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestDorisApplyFlow(TestFlowBase, TestCase):
    """
    DORIS APPLY测试类。
    """

    # DORIS apply: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
    def test_doris_single_apply_flow(self):
        self.flow_test(client, DORIS_APPLY_TICKET_DATA)

    # DORIS disable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_disable_flow(self):
        self.flow_test(client, DORIS_DISABLE_TICKET_DATA)

    # DORIS enable: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_enable_flow(self):
        self.flow_test(client, DORIS_ENABLE_TICKET_DATA)

    # DORIS destroy: start --> itsm --> PAUSE --> INNER_FLOW --> end
    def test_doris_destroy_flow(self):
        self.flow_test(client, DORIS_DESTROY_TICKET_DATA)

    def apply_patches(self):
        # 扩展基类的apply_patches方法来包括新的patch
        super().apply_patches()

        # 定义并启动新的patch
        mock_resource_apply_patch = patch(
            "backend.ticket.flow_manager.resource.ResourceApplyFlow.apply_resource",
            lambda resource_request_id, node_infos: (1, DORIS_SOURCE_APPLICATION_DATA),
        )
        # 启动新的patch并添加到self.mocks列表中以便随后可以停止它
        self.mocks.extend([mock_resource_apply_patch.start()])

    def setup(self):
        """
        测试的初始设置。
        """
        Spec.objects.all().delete()
        Spec.objects.bulk_create([Spec(**data) for data in DORIS_SPEC_DATA])
        Cluster.objects.bulk_create([Cluster(**data) for data in DORIS_CLUSTER_DATA])
        super().setup()

    def teardown(self):
        """
        清理数据环境。
        """
        DBModule.objects.all().delete()
        Spec.objects.all().delete()
        Cluster.objects.all().delete()
        StorageInstance.objects.all().delete()
        Machine.objects.all().delete()

        super().teardown()
