"""
Notify模块测试基类和工具方法
"""
from unittest.mock import patch

from django.test import TestCase

from backend.tests.mock_data.components.bkchat import (
    BKCHAT_SEND_MSG_FAILURE_RESPONSE,
    BKCHAT_SEND_MSG_SUCCESS_RESPONSE,
)
from backend.tests.mock_data.components.cmsi import CMSI_SEND_MSG_FAILURE_RESPONSE, CMSI_SEND_MSG_SUCCESS_RESPONSE
from backend.tests.mock_data.ticket.create_ticket import create_mock_ticket


class BaseNotifyTestCase(TestCase):
    """Notify模块测试基类"""

    def setUp(self):
        super().setUp()
        self.mock_ticket = create_mock_ticket()

    def create_mock_notify_adapter(self, **kwargs):
        """创建mock的NotifyAdapter"""
        from backend.core.notify.handlers import NotifyAdapter

        # 默认参数
        defaults = {"ticket_id": self.mock_ticket.id, "username": "admin", "context": {"test": "data"}}
        defaults.update(kwargs)

        return NotifyAdapter(**defaults)

    def setup_cmsi_mock(self, mock_send_msg, success=True):
        """设置CMSI API mock"""
        response = CMSI_SEND_MSG_SUCCESS_RESPONSE if success else CMSI_SEND_MSG_FAILURE_RESPONSE
        mock_send_msg.return_value = response

    def setup_bkchat_mock(self, mock_send_msg, success=True):
        """设置BkChat API mock"""
        response = BKCHAT_SEND_MSG_SUCCESS_RESPONSE if success else BKCHAT_SEND_MSG_FAILURE_RESPONSE
        mock_send_msg.return_value = response

    def setup_ticket_mocks(
        self, mock_ticket_get, mock_get_assistance, mock_app_cache_get, ticket=None, app_cache=None
    ):
        """设置工单相关的mock"""
        from backend.tests.mock_data.ticket.create_ticket import DEFAULT_APP_CACHE_MOCK, DEFAULT_TICKET_MOCK

        mock_ticket_get.return_value = ticket or DEFAULT_TICKET_MOCK
        mock_get_assistance.return_value = ["helper1"]
        if mock_app_cache_get is not None:
            mock_app_cache_get.return_value = app_cache or DEFAULT_APP_CACHE_MOCK

    def mock_ticket_get(self, ticket=None):
        """Mock Ticket.objects.get"""
        if ticket is None:
            ticket = self.mock_ticket
        return patch("backend.ticket.models.Ticket.objects.get", return_value=ticket)

    def create_mock_context(self, **kwargs):
        """创建mock上下文"""
        defaults = {
            "ticket_id": self.mock_ticket.id,
            "bk_biz_id": self.mock_ticket.bk_biz_id,
            "creator": self.mock_ticket.creator,
            "title": "Test Notification",
        }
        defaults.update(kwargs)
        return defaults
