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
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_services.taskflow.views.flow import TaskFlowViewSet
from backend.flow.models import FlowNode, FlowTree, StateType
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.bklog import BKLogApiMock
from backend.tests.mock_data.db_services import taskflow
from backend.ticket.constants import TicketType

logger = logging.getLogger("test")
client = APIClient()
pytestmark = pytest.mark.django_db


@pytest.fixture
def init_taskflow():
    FlowTree.objects.create(
        uid=425,
        tree=taskflow.TREE_DATA,
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SEMANTIC_CHECK.value,
        root_id=taskflow.ROOT_ID,
        status=StateType.FINISHED.value,
    )
    FlowNode.objects.create(
        uid=425,
        root_id=taskflow.ROOT_ID,
        node_id=taskflow.NODE_ID,
        status=StateType.FINISHED.value,
        version_id=taskflow.VERSION_ID,
    )


class TestTaskflowApi:
    """
    测试taskflow相关api
    """

    def __init__(self):
        patch.object(settings, "MIDDLEWARE", [])

    root_id = taskflow.ROOT_ID
    node_id = taskflow.NODE_ID
    version_id = taskflow.VERSION_ID

    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_taskflow_retrieve(self, mocked_permission_classes, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]

        url = f"/apis/taskflow/{self.root_id}/"
        data = client.get(url).data
        assert data["flow_info"]["root_id"] == self.root_id

    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_histories(self, mocked_permission_classes, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]

        url = f"/apis/taskflow/{self.root_id}/node_histories/"
        data = client.get(url, data={"node_id": self.node_id}).data

        assert len(data) == 1
        assert data[0]["version"] == self.version_id

    @patch("backend.db_services.taskflow.handlers.BKLogApi", BKLogApiMock)
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log(self, mocked_permission_classes, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(url, data={"node_id": self.node_id, "version_id": "1"}).data

        assert len(data) == 2
