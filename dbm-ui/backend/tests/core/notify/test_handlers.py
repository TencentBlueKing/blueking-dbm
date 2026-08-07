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
        """test send_msg task execution failure"""
        mock_adapter_class.side_effect = Exception("test exception")

        with pytest.raises(Exception):
            handlers.send_msg(ticket_id=123)


class TestSplitContent:
    """Test _split_content with code block and table block awareness"""

    # ==================== basic splitting logic ====================

    def test_short_content_no_split(self):
        """short content should not be split"""
        content = "hello world"
        result = handlers._split_content(content, max_length=100)
        assert result == ["hello world"]

    def test_exact_max_length_no_split(self):
        """content exactly at max_length should not be split"""
        content = "a" * 100
        result = handlers._split_content(content, max_length=100)
        assert result == [content]

    def test_normal_lines_split_by_line(self):
        """normal multi-line text should be split by line"""
        lines = [f"line{i}" for i in range(20)]
        content = "\n".join(lines)
        result = handlers._split_content(content, max_length=50)
        # all chunks should not exceed the limit
        for chunk in result:
            assert len(chunk) <= 50
        # reassembled content should be complete
        assert "\n".join(result) == content

    def test_single_long_line_force_split(self):
        """a single long line should be force-split by characters"""
        content = "x" * 250
        result = handlers._split_content(content, max_length=100)
        assert len(result) == 3
        assert result[0] == "x" * 100
        assert result[1] == "x" * 100
        assert result[2] == "x" * 50

    # ==================== code block awareness ====================

    def test_code_block_kept_intact(self):
        """code block should be kept as a whole"""
        content = "prefix text\n```sql\nSELECT * FROM users;\nWHERE id = 1;\n```\nsuffix text"
        result = handlers._split_content(content, max_length=60)
        # code block should be intact in some chunk
        code_block = "```sql\nSELECT * FROM users;\nWHERE id = 1;\n```"
        found = any(code_block in chunk for chunk in result)
        assert found, f"code block not intact, result: {result}"

    def test_code_block_with_language_tag(self):
        """code block with language tag should be kept intact"""
        content = "intro text\n```python\ndef hello():\n    print('world')\n```\nend"
        result = handlers._split_content(content, max_length=70)
        code_block = "```python\ndef hello():\n    print('world')\n```"
        found = any(code_block in chunk for chunk in result)
        assert found, f"code block not intact, result: {result}"

    def test_multiple_code_blocks_kept_intact(self):
        """multiple code blocks should each be kept intact"""
        content = "first part\n" "```sql\nSELECT 1;\n```\n" "middle text\n" "```bash\necho hello\n```\n" "end"
        result = handlers._split_content(content, max_length=50)
        # each chunk with ``` must have matching closing fence
        for chunk in result:
            fence_count = chunk.count("```")
            assert fence_count % 2 == 0, f"unclosed code block in chunk: {chunk}"

    def test_code_block_separated_from_surrounding_text(self):
        """code block should go to a new chunk when capacity is insufficient"""
        # prefix fills most of the space, code block should start a new chunk
        prefix = "a" * 80
        code = "```\ncode line\n```"
        content = f"{prefix}\n{code}\nend"
        result = handlers._split_content(content, max_length=100)
        # code block should not be truncated
        assert any("```\ncode line\n```" in chunk for chunk in result)

    def test_unclosed_code_block_treated_as_block(self):
        """unclosed code block (until end of content) should be treated as a whole"""
        content = "prefix\n```python\nsome code\nmore code"
        result = handlers._split_content(content, max_length=40)
        # unclosed code block should be kept as a whole
        code_part = "```python\nsome code\nmore code"
        found = any(code_part in chunk for chunk in result)
        assert found, f"unclosed code block not intact, result: {result}"

    # ==================== table block awareness ====================

    def test_table_block_kept_intact(self):
        """table block should be kept as a whole"""
        content = (
            "intro text\n"
            "| col1 | col2 | col3 |\n"
            "| --- | --- | --- |\n"
            "| val1 | val2 | val3 |\n"
            "| val4 | val5 | val6 |\n"
            "suffix text"
        )
        result = handlers._split_content(content, max_length=120)
        # header, separator, and data rows should be in the same chunk
        table_block = (
            "| col1 | col2 | col3 |\n" "| --- | --- | --- |\n" "| val1 | val2 | val3 |\n" "| val4 | val5 | val6 |"
        )
        found = any(table_block in chunk for chunk in result)
        assert found, f"table not intact, result: {result}"

    def test_table_header_and_separator_not_split(self):
        """table header and separator should not be separated"""
        content = "a" * 90 + "\n" "| name | age |\n" "| --- | --- |\n" "| tom | 18 |\n" "end"
        result = handlers._split_content(content, max_length=100)
        # header and separator must be in the same chunk
        for chunk in result:
            if "| name | age |" in chunk:
                assert "| --- | --- |" in chunk, f"header and separator split: {result}"
                break

    def test_table_separated_from_preceding_text(self):
        """table should go to a new chunk when capacity is insufficient"""
        prefix = "x" * 80
        table = "| a | b |\n| - | - |\n| 1 | 2 |"
        content = f"{prefix}\n{table}\nend"
        result = handlers._split_content(content, max_length=100)
        # table should be intact
        assert any("| a | b |\n| - | - |\n| 1 | 2 |" in chunk for chunk in result)

    def test_multiple_tables_each_kept_intact(self):
        """multiple tables should each be kept intact"""
        content = (
            "table1:\n"
            "| h1 | h2 |\n| -- | -- |\n| v1 | v2 |\n"
            "table2:\n"
            "| h3 | h4 |\n| -- | -- |\n| v3 | v4 |\n"
            "end"
        )
        result = handlers._split_content(content, max_length=80)
        table1 = "| h1 | h2 |\n| -- | -- |\n| v1 | v2 |"
        table2 = "| h3 | h4 |\n| -- | -- |\n| v3 | v4 |"
        assert any(table1 in chunk for chunk in result), f"table1 split: {result}"
        assert any(table2 in chunk for chunk in result), f"table2 split: {result}"

    # ==================== mixed scenarios ====================

    def test_code_block_and_table_mixed(self):
        """code block and table mixed scenario"""
        content = "title\n" "```sql\nSELECT 1;\n```\n" "table:\n" "| id | name |\n| -- | ---- |\n| 1  | test |\n" "end"
        result = handlers._split_content(content, max_length=80)
        # code block intact
        assert any("```sql\nSELECT 1;\n```" in chunk for chunk in result)
        # table intact
        assert any("| id | name |\n| -- | ---- |\n| 1  | test |" in chunk for chunk in result)

    def test_content_integrity_after_split(self):
        """reassembled content should match the original"""
        content = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8"
        result = handlers._split_content(content, max_length=30)
        reassembled = "\n".join(result)
        assert reassembled == content

    def test_empty_content(self):
        """empty content should return a single-element list"""
        result = handlers._split_content("", max_length=100)
        assert result == [""]

    def test_content_with_only_code_block(self):
        """content with only a code block"""
        content = "```\nhello\nworld\n```"
        result = handlers._split_content(content, max_length=100)
        assert result == [content]

    def test_content_with_only_table(self):
        """content with only a table"""
        content = "| a | b |\n| - | - |\n| 1 | 2 |"
        result = handlers._split_content(content, max_length=100)
        assert result == [content]


class TestIsTableLine:
    """Test _is_table_line helper function"""

    def test_standard_table_line(self):
        """standard table line"""
        assert handlers._is_table_line("| col1 | col2 |") is True

    def test_separator_line(self):
        """table separator line"""
        assert handlers._is_table_line("| --- | --- |") is True
        assert handlers._is_table_line("| :--- | ---: |") is True

    def test_table_line_with_leading_spaces(self):
        """table line with leading spaces"""
        assert handlers._is_table_line("  | col1 | col2 |") is True

    def test_non_table_line(self):
        """non-table line"""
        assert handlers._is_table_line("normal text") is False
        assert handlers._is_table_line("```") is False
        assert handlers._is_table_line("> quote") is False

    def test_pipe_only_at_start(self):
        """pipe only at the start but not at the end"""
        assert handlers._is_table_line("| not a table") is False

    def test_pipe_only_at_end(self):
        """pipe only at the end but not at the start"""
        assert handlers._is_table_line("not a table |") is False

    def test_empty_line(self):
        """empty line"""
        assert handlers._is_table_line("") is False

    def test_single_pipe(self):
        """single pipe character"""
        assert handlers._is_table_line("|") is False
