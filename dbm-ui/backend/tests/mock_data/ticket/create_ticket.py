# -*- coding: utf-8 -*-
"""
工单相关的Mock数据
"""
from unittest.mock import Mock


def create_mock_ticket(
    ticket_id=123,
    bk_biz_id=1,
    creator="admin",
    status="pending",
    ticket_type="mysql_single_apply",
    remark="测试工单",
    url=None,
    operators=None,
    helpers=None,
):
    """创建Mock工单对象"""
    mock_ticket = Mock()
    mock_ticket.id = ticket_id
    mock_ticket.bk_biz_id = bk_biz_id
    mock_ticket.creator = creator
    mock_ticket.status = status
    mock_ticket.ticket_type = ticket_type
    mock_ticket.details = {"clusters": {}}
    mock_ticket.msg_config = {}
    mock_ticket.remark = remark

    # 时间相关mock
    mock_time = Mock()
    mock_time.astimezone.return_value.strftime.return_value = "2023-01-01 00:00:00+0800"
    mock_ticket.create_at = mock_time
    mock_ticket.update_at = mock_time

    # URL
    mock_ticket.url = url or f"http://test.com/ticket/{ticket_id}"

    # 操作者和协助者
    default_operators = operators or ["user1"]
    default_helpers = helpers or ["user2"]
    mock_ticket.get_current_operators.return_value = {"operators": default_operators, "helpers": default_helpers}

    # 其他方法
    mock_ticket.get_terminate_reason.return_value = ""

    return mock_ticket


def create_mock_app_cache(bk_biz_name="测试业务", db_app_abbr="test"):
    """创建Mock应用缓存对象"""
    mock_app = Mock()
    mock_app.bk_biz_name = bk_biz_name
    mock_app.db_app_abbr = db_app_abbr
    return mock_app


# 常用的工单mock数据
DEFAULT_TICKET_MOCK = create_mock_ticket()
PENDING_TICKET_MOCK = create_mock_ticket(status="pending")
RUNNING_TICKET_MOCK = create_mock_ticket(status="running")
SUCCESS_TICKET_MOCK = create_mock_ticket(status="success")
FAILED_TICKET_MOCK = create_mock_ticket(status="failed")

# 常用的应用缓存mock数据
DEFAULT_APP_CACHE_MOCK = create_mock_app_cache()
