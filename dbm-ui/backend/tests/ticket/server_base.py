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
from unittest.mock import PropertyMock, patch

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.handlers.password import DBPasswordHandler
from backend.core import notify
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.dbresource import DBResourceApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.components.nodeman import NodemanApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.ticket_flow import PASSWORD, ROOT_ID
from backend.ticket.constants import TicketFlowStatus, TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.handler import TicketHandler
from backend.ticket.models import ClusterOperateRecordManager, Ticket, TicketFlowsConfig
from backend.ticket.views import TicketViewSet

pytestmark = pytest.mark.django_db


class BaseTicketTest:
    """
    测试流程的基类。
    """

    # 默认单据测试的patch
    patches = [
        patch.object(TicketViewSet, "permission_classes", return_value=[AllowAny]),
        patch.object(InnerFlow, "_run", return_value=ROOT_ID),
        patch.object(InnerFlow, "status", new_callable=PropertyMock, return_value=TicketStatus.SUCCEEDED),
        patch.object(PauseFlow, "status", new_callable=PropertyMock, return_value=TicketFlowStatus.SKIPPED),
        patch.object(DBPasswordHandler, "get_random_password", return_value=PASSWORD),
        patch.object(notify.send_msg, "apply_async", return_value="this is a test msg"),
        patch.object(TicketViewSet, "get_permissions"),
        patch.object(settings, "MIDDLEWARE", return_value=[]),
        patch.object(ClusterOperateRecordManager, "get_exclusive_ticket_map", return_value=[]),
        patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock()),
        patch("backend.db_services.cmdb.biz.Permission", PermissionMock),
        patch("backend.ticket.flow_manager.resource.DBResourceApi", DBResourceApiMock),
        patch("backend.db_services.dbresource.handlers.CCApi", CCApiMock()),
        patch("backend.db_services.cmdb.biz.CCApi", CCApiMock()),
        patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock()),
        patch("backend.db_services.ipchooser.query.resource.BKNodeManApi", NodemanApiMock()),
    ]
    # 默认测试请求客户端
    client = APIClient()
    # 默认单据配置
    ticket_config_map = {}

    @classmethod
    def apply_patches(cls):
        [patcher.start() for patcher in cls.patches]

    @classmethod
    def stop_patches(cls):
        [patcher.stop() for patcher in cls.patches]

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, django_db_setup, django_db_blocker):
        """
        测试类的初始化(替换原 setUpClass 的类级别初始化)
        """
        with django_db_blocker.unblock():
            # 初始化单据配置
            TicketHandler.ticket_flow_config_init()
            self.ticket_config_map = {config.ticket_type: config.configs for config in TicketFlowsConfig.objects.all()}

            # 启动所有 Mock
            self.apply_patches()

            # 初始化客户端并登录
            self.client = APIClient()
            self.client.login(username="admin")

            yield

            # 停止 Mock
            self.stop_patches()

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """测试方法的初始设置(替换原 setUp/tearDown)"""
        yield

    def flow_test(self, ticket_data):
        """
        基本的单据测试，只看单据是否能跑通
        """
        itsm_data = copy.deepcopy(ticket_data)
        resp = self.client.post("/apis/tickets/", data=itsm_data)
        assert status.is_success(resp.status_code)

        ticket = Ticket.objects.get(id=resp.data["id"])
        current_flow = None

        while ticket.next_flow() is not None:
            last_flow, current_flow = current_flow, ticket.current_flow()
            assert not last_flow or (last_flow and last_flow.id != current_flow.id), f"flow[{current_flow.id}]流转失败"

            resp = self.client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
            assert status.is_success(resp.status_code), f"response 请求错误: {resp.status_code}"
