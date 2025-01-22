import copy
from unittest import TestCase
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
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.ticket_flow import PASSWORD, ROOT_ID
from backend.ticket.constants import TicketFlowStatus, TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.handler import TicketHandler
from backend.ticket.models import ClusterOperateRecordManager, Ticket, TicketFlowsConfig
from backend.ticket.views import TicketViewSet

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class BaseTicketTest(TestCase):
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
        patch("backend.db_services.cmdb.biz.CCApi", CCApiMock()),
        patch("backend.db_services.cmdb.biz.Permission", PermissionMock),
        patch("backend.ticket.flow_manager.resource.DBResourceApi", DBResourceApiMock),
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

    @classmethod
    def setUpClass(cls) -> None:
        """
        测试类的初始化
        """
        # 初始化单据配置
        TicketHandler.ticket_flow_config_init()
        cls.ticket_config_map = {config.ticket_type: config.configs for config in TicketFlowsConfig.objects.all()}
        # 初始化客户端，用admin登录
        cls.client.login(username="admin")
        # 初始化mock
        cls.apply_patches()

    @classmethod
    def tearDownClass(cls) -> None:
        # 停止mock
        cls.stop_patches()

    def setUp(self):
        """
        测试方法的初始设置。
        """
        pass

    def tearDown(self):
        """
        测试方法完成后的清理工作。
        """
        pass

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
