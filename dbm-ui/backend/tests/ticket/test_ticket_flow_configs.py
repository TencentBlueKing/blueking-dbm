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
import copy
import logging
from unittest.mock import PropertyMock, patch

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.tests.mock_data.ticket.mysql_flow import (
    MYSQL_AUTHORIZE_CLONE_CLIENT_TICKET_DATA,
    MYSQL_CLONE_CLIENT_TICKET_CONFIG,
)
from backend.tests.mock_data.ticket.ticket_flow import ROOT_ID
from backend.ticket.constants import FlowType, TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Ticket, TicketFlowsConfig
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()


# 初始化单据流程配置
@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        TicketHandler.ticket_flow_config_init()
        yield
        TicketFlowsConfig.objects.all().delete()


class TestTicketFlowsConfig:
    """
    测试单据流程设置
    """

    @patch.object(settings, "MIDDLEWARE", [])
    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    def test_ticket_flows_config(self, mocked_status, mocked__run, mocked_permission_classes, db):
        """
        以mysql客户端权限克隆为例，测试单据流程设置
        """
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")

        clone_data = copy.deepcopy(MYSQL_AUTHORIZE_CLONE_CLIENT_TICKET_DATA)
        details = clone_data["details"]
        cache.set(details["clone_uid"], details["clone_data_list"])

        # 创建客户端克隆业务配置，使其拥有itsm和人工确认节点
        TicketFlowsConfig.objects.create(**MYSQL_CLONE_CLIENT_TICKET_CONFIG)

        resp = client.post("/apis/tickets/", data=clone_data)
        flows = list(Ticket.objects.get(id=resp.data["id"]).flows.all())
        assert len(flows) == 3
        assert flows[0].flow_type == FlowType.BK_ITSM
        assert flows[1].flow_type == FlowType.PAUSE
        assert flows[2].flow_type == FlowType.INNER_FLOW

        # 其他业务不受影响，仍然继承平台配置
        another_clone_data = copy.deepcopy(clone_data)
        another_clone_data["bk_biz_id"] = 3
        resp = client.post("/apis/tickets/", data=another_clone_data)
        flows = list(Ticket.objects.get(id=resp.data["id"]).flows.all())
        assert len(flows) == 1 and flows[0].flow_type == FlowType.INNER_FLOW

        # 删除业务配置，则此时使用平台配置
        TicketFlowsConfig.objects.filter(**MYSQL_CLONE_CLIENT_TICKET_CONFIG).delete()

        resp = client.post("/apis/tickets/", data=clone_data)
        flows = list(Ticket.objects.get(id=resp.data["id"]).flows.all())
        assert len(flows) == 1 and flows[0].flow_type == FlowType.INNER_FLOW
