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
from unittest.mock import Mock, patch

import pytest

from backend.core.notify import handlers
from backend.core.notify.constants import MsgType
from backend.tests.core.notify.base import BaseNotifyTestCase
from backend.tests.mock_data.ticket.create_ticket import create_mock_ticket


class TestNotifyHandlerFunctionality(BaseNotifyTestCase):
    """测试通知处理器功能"""

    @patch("backend.components.bkchat.client.BkChatApi.send_ticket_msg")
    def test_bk_chat_handler_send_notification(self, mock_send_msg):
        """测试BkChat处理器发送通知"""
        self.setup_bkchat_mock(mock_send_msg, success=True)

        handler = handlers.BkChatHandler("测试标题", "测试内容", ["user1"])
        mock_ticket = create_mock_ticket()
        context = {"ticket": mock_ticket, "phase": "pending", "receivers": ["user1"]}

        handler.send_msg(MsgType.RTX.value, context)
        mock_send_msg.assert_called_once()

    @patch("backend.components.CmsiApi.send_msg")
    def test_cmsi_handler_send_notification(self, mock_send_msg):
        """测试Cmsi处理器发送通知"""
        self.setup_cmsi_mock(mock_send_msg, success=True)

        handler = handlers.CmsiHandler("测试标题", "测试内容", ["user1"])
        # 测试一个代表性方法
        handler.send_mail()
        mock_send_msg.assert_called_once()

    def test_cmsi_handler_send_unknown_type(self):
        """测试Cmsi处理器发送未知类型通知"""
        handler = handlers.CmsiHandler("测试标题", "测试内容", ["user1"])
        with pytest.raises(AttributeError):
            handler.send_msg("unknown", {})


@pytest.mark.django_db
class TestNotifyAdapterFunctionality(BaseNotifyTestCase):
    """测试通知适配器功能"""

    @patch("backend.env.BKCHAT_APIGW_DOMAIN", "http://test-bkchat.com")
    @patch("backend.components.cmsi.client.CmsiApi.get_msg_type")
    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    def test_notify_adapter_get_handler_functionality(self, mock_get_assistance, mock_ticket_get, mock_get_msg_type):
        """测试通知适配器获取处理器功能"""
        # Mock CMSI API调用
        mock_get_msg_type.return_value = [{"type": "mail"}, {"type": "sms"}, {"type": "voice"}, {"type": "weixin"}]

        # 使用简化的mock设置
        self.setup_ticket_mocks(mock_ticket_get, mock_get_assistance, None)

        adapter = handlers.NotifyAdapter(ticket_id=123)

        # 测试获取BkChat处理器
        notify_class, context = adapter.get_notify_class(MsgType.RTX.value)
        assert notify_class == handlers.BkChatHandler
        assert "ticket" in context

        # 测试获取Cmsi处理器
        notify_class, context = adapter.get_notify_class(MsgType.MAIL.value)
        assert notify_class == handlers.CmsiHandler
        assert context == {}

    @patch("backend.env.BKCHAT_APIGW_DOMAIN", "http://test-bkchat.com")
    @patch("backend.components.cmsi.client.CmsiApi.get_msg_type")
    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    @patch("backend.configuration.models.BizSettings.get_setting_value")
    @patch("backend.components.bkchat.client.BkChatApi.send_ticket_msg")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_notify_adapter_send_bk_chat_notification(
        self,
        mock_app_cache_get,
        mock_send_msg,
        mock_get_setting,
        mock_get_assistance,
        mock_ticket_get,
        mock_get_msg_type,
    ):
        """测试通知适配器发送BkChat通知功能"""
        # Mock CMSI API调用
        mock_get_msg_type.return_value = [{"type": "mail"}, {"type": "sms"}, {"type": "voice"}, {"type": "weixin"}]

        # 使用简化的mock设置
        ticket = create_mock_ticket(ticket_type="mysql_single_apply")
        self.setup_ticket_mocks(mock_ticket_get, mock_get_assistance, mock_app_cache_get, ticket=ticket)
        self.setup_bkchat_mock(mock_send_msg, success=True)

        mock_get_setting.return_value = {"pending": {"rtx": True}}

        adapter = handlers.NotifyAdapter(ticket_id=123)
        adapter.send_msg()

        # 验证API被调用
        mock_send_msg.assert_called_once()

    @patch("backend.components.cmsi.client.CmsiApi.get_msg_type")
    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    @patch("backend.configuration.models.BizSettings.get_setting_value")
    @patch("backend.components.CmsiApi.send_msg")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_notify_adapter_send_cmsi_notification(
        self,
        mock_app_cache_get,
        mock_send_msg,
        mock_get_setting,
        mock_get_assistance,
        mock_ticket_get,
        mock_get_msg_type,
    ):
        """测试通知适配器发送Cmsi通知功能"""
        # Mock CMSI API调用
        mock_get_msg_type.return_value = [{"type": "mail"}, {"type": "sms"}, {"type": "voice"}, {"type": "weixin"}]

        # 使用简化的mock设置
        ticket = create_mock_ticket(ticket_type="mysql_single_apply")
        self.setup_ticket_mocks(mock_ticket_get, mock_get_assistance, mock_app_cache_get, ticket=ticket)
        self.setup_cmsi_mock(mock_send_msg, success=True)

        mock_get_setting.return_value = {"pending": {"mail": True}}

        adapter = handlers.NotifyAdapter(ticket_id=123)
        adapter.send_msg()

        # 验证API被调用
        mock_send_msg.assert_called_once()

    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    def test_notify_adapter_send_unknown_handler_notification(self, mock_get_assistance, mock_ticket_get):
        """测试通知适配器发送未知处理器通知功能"""
        # 使用简化的mock设置
        self.setup_ticket_mocks(mock_ticket_get, mock_get_assistance, None)

        adapter = handlers.NotifyAdapter(ticket_id=123)
        notify_class, context = adapter.get_notify_class("unknown_type")

        # 未知类型应该返回CmsiHandler
        assert notify_class == handlers.CmsiHandler

    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_notify_adapter_send_notification_with_ticket_info(
        self, mock_app_cache_get, mock_get_assistance, mock_ticket_get
    ):
        """测试通知适配器发送带工单信息的通知功能"""
        # 使用简化的mock设置
        ticket = create_mock_ticket(ticket_type="mysql_single_apply")
        self.setup_ticket_mocks(mock_ticket_get, mock_get_assistance, mock_app_cache_get, ticket=ticket)

        adapter = handlers.NotifyAdapter(ticket_id=123)

        # 测试渲染消息模板
        title, content = adapter.render_msg_template(MsgType.MAIL.value)

        assert "DBM" in title
        assert "123" in title

    @patch("backend.ticket.models.Ticket.objects.get")
    @patch("backend.configuration.models.BizSettings.get_assistance")
    def test_notify_adapter_send_notification_with_receivers(self, mock_get_assistance, mock_ticket_get):
        """测试通知适配器发送带接收者的通知功能"""
        # 使用简化的mock设置
        ticket = create_mock_ticket(creator="admin")
        mock_ticket_get.return_value = ticket
        mock_get_assistance.return_value = ["helper1", "helper2"]

        adapter = handlers.NotifyAdapter(ticket_id=123)
        receivers = adapter.get_receivers()

        # 验证接收者包含创建者和协助人
        assert "admin" in receivers
        assert "helper1" in receivers
        assert "helper2" in receivers


@pytest.mark.django_db
class TestSendMsgTaskFunctionality:
    """测试send_msg任务功能"""

    @patch("backend.core.notify.handlers.NotifyAdapter")
    def test_send_msg_task_execution(self, mock_adapter_class):
        """测试send_msg任务执行"""
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter
        mock_adapter.send_msg.return_value = None

        handlers.send_msg(ticket_id=123)

        mock_adapter_class.assert_called_once_with(123, None)
        mock_adapter.send_msg.assert_called_once()

    @patch("backend.core.notify.handlers.NotifyAdapter")
    def test_send_msg_task_failure(self, mock_adapter_class):
        """测试send_msg任务执行失败"""
        mock_adapter_class.side_effect = Exception("测试异常")

        with pytest.raises(Exception):
            handlers.send_msg(ticket_id=123)
