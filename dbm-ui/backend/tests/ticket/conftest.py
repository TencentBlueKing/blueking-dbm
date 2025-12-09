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

from backend.tests.mock_data import constant
from backend.ticket.constants import FlowType, TicketStatus, TicketType, TodoStatus, TodoType
from backend.ticket.models import Flow, Ticket, Todo


@pytest.fixture
def test_ticket_bk_biz_id():
    """提供测试业务ID"""
    return constant.BK_BIZ_ID


@pytest.fixture
def test_mysql_single_apply_ticket(test_ticket_bk_biz_id):
    """创建MySQL单机部署单据"""
    ticket = Ticket.objects.create(
        id=1001,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.PENDING,
        creator="admin",
        updater="admin",
        remark="test mysql single apply ticket",
        details={
            "nodes": {"backend": []},
            "ip_source": "manual_input",
            "bk_cloud_id": 0,
            "city_code": "",
            "spec": "",
            "db_module_id": 111,
            "cluster_count": 1,
            "inst_num": 1,
            "domains": [{"key": "test_cluster"}],
            "charset": "utf8mb4",
            "db_version": "MySQL-5.7",
            "resource_spec": {},
        },
        group=TicketType.MYSQL_SINGLE_APPLY.value,
    )
    yield ticket
    ticket.delete()


@pytest.fixture
def test_running_ticket_with_flow(test_ticket_bk_biz_id):
    """创建正在执行的单据(包含flow)"""
    ticket = Ticket.objects.create(
        id=1002,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test running ticket",
        details={
            "nodes": {},
            "cluster_ids": [1, 2, 3],
            "bk_cloud_id": 0,
            "city_code": "",
            "spec": "",
            "db_module_id": 111,
            "cluster_count": 1,
            "inst_num": 1,
            "domains": [{"key": "running_cluster"}],
            "charset": "utf8mb4",
            "db_version": "MySQL-5.7",
            "resource_spec": {},
        },
        group=TicketType.MYSQL_HA_APPLY.value,
    )

    # 创建关联的Flow
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="MySQL部署流程",
        status=TicketStatus.RUNNING,
    )

    yield ticket, flow

    flow.delete()
    ticket.delete()


@pytest.fixture
def test_ticket_with_todo(test_ticket_bk_biz_id):
    """创建带有待办的单据"""
    ticket = Ticket.objects.create(
        id=1003,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test ticket with todo",
        details={
            "nodes": {},
            "bk_cloud_id": 0,
            "city_code": "",
            "spec": "",
            "db_module_id": 111,
            "cluster_count": 1,
            "inst_num": 1,
            "domains": [{"key": "todo_cluster"}],
            "charset": "utf8mb4",
            "db_version": "MySQL-5.7",
            "resource_spec": {},
        },
        group=TicketType.MYSQL_HA_APPLY.value,
    )

    # 创建关联的Flow
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="待办流程",
        status=TicketStatus.RUNNING,
    )

    # 创建关联的Todo
    todo = Todo.objects.create(
        ticket=ticket,
        flow=flow,
        name="人工确认",
        type=TodoType.INNER_APPROVE,
        status=TodoStatus.TODO,
        operators=["admin", "dba1"],
        context={"message": "请确认是否继续执行"},
    )

    yield ticket, flow, todo

    todo.delete()
    flow.delete()
    ticket.delete()


@pytest.fixture
def test_multiple_tickets(test_ticket_bk_biz_id):
    """创建多个测试单据用于列表查询"""
    tickets = []

    # 创建不同状态的单据
    ticket_configs = [
        {"id": 1010, "status": TicketStatus.PENDING, "ticket_type": TicketType.MYSQL_SINGLE_APPLY},
        {"id": 1011, "status": TicketStatus.RUNNING, "ticket_type": TicketType.MYSQL_HA_APPLY},
        {"id": 1012, "status": TicketStatus.SUCCEEDED, "ticket_type": TicketType.MYSQL_IMPORT_SQLFILE},
        {"id": 1013, "status": TicketStatus.FAILED, "ticket_type": TicketType.MYSQL_CHECKSUM},
        {"id": 1014, "status": TicketStatus.REVOKED, "ticket_type": TicketType.MYSQL_PROXY_ADD},
    ]

    for config in ticket_configs:
        ticket = Ticket.objects.create(
            id=config["id"],
            bk_biz_id=test_ticket_bk_biz_id,
            ticket_type=config["ticket_type"],
            status=config["status"],
            creator="admin",
            updater="admin",
            remark=f"test ticket {config['id']}",
            details={"nodes": {}},
            group=config["ticket_type"].value,
        )
        tickets.append(ticket)

    yield tickets

    for ticket in tickets:
        ticket.delete()


@pytest.fixture
def test_succeeded_ticket(test_ticket_bk_biz_id):
    """创建已完成的单据"""
    ticket = Ticket.objects.create(
        id=1020,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.SUCCEEDED,
        creator="admin",
        updater="admin",
        remark="test succeeded ticket",
        details={"nodes": {}},
        group=TicketType.MYSQL_SINGLE_APPLY.value,
    )
    yield ticket
    ticket.delete()
