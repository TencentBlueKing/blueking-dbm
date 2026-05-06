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
from unittest.mock import MagicMock, patch

import pytest

from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.tests.mock_data.components import cc
from backend.ticket.constants import (
    SPECIAL_APPROVE_TICKETS,
    FlowType,
    FlowTypeConfig,
    OperateNodeActionType,
    TicketFlowStatus,
    TicketStatus,
    TicketType,
    TodoStatus,
    TodoType,
)
from backend.ticket.exceptions import TicketFlowsConfigException
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Flow, Ticket, TicketFlowsConfig, Todo
from backend.ticket.todos import TodoActionType

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")


@pytest.fixture(autouse=True)
def mock_flow_signal():
    """自动断开 Flow 的 post_save 信号，避免触发真实的 ITSM/TicketFlowManager 调用"""
    from django.db.models.signals import post_save

    from backend.ticket.models import Flow as FlowModel
    from backend.ticket.signals import update_ticket_status

    post_save.disconnect(update_ticket_status, sender=FlowModel)
    yield
    post_save.connect(update_ticket_status, sender=FlowModel)


@pytest.fixture
def init_ticket_with_clusters(test_ticket_bk_biz_id):
    """创建带有集群快照信息的单据"""
    ticket = Ticket.objects.create(
        id=2001,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test ticket with clusters",
        details={
            "nodes": {},
            "cluster_ids": [100, 200],
            "clusters": {
                "100": {"immute_domain": "cluster100.db.com"},
                "200": {"immute_domain": "cluster200.db.com"},
            },
        },
        group=TicketType.MYSQL_SINGLE_APPLY.value,
    )
    yield ticket
    ticket.delete()


@pytest.fixture
def init_ticket_with_instances(test_ticket_bk_biz_id):
    """创建带有实例快照信息的单据"""
    ticket = Ticket.objects.create(
        id=2002,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test ticket with instances",
        details={
            "nodes": {},
            "instance_ids": [301, 302],
            "instances": {
                "301": {"instance": f"{cc.NORMAL_IP}:3306"},
                "302": {"instance": f"{cc.NORMAL_IP2}:3306"},
            },
        },
        group=TicketType.MYSQL_SINGLE_APPLY.value,
    )
    yield ticket
    ticket.delete()


@pytest.fixture
def init_itsm_flow(test_ticket_bk_biz_id):
    """创建带有 ITSM 审批流程的单据（信号已由 mock_flow_signal 自动断开）"""
    ticket = Ticket.objects.create(
        id=2003,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test itsm flow ticket",
        details={"nodes": {}},
        group=TicketType.MYSQL_SINGLE_APPLY.value,
    )
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.BK_ITSM,
        flow_alias="ITSM审批",
        flow_obj_id="REQ20200831000005",
        status=TicketFlowStatus.RUNNING,
        details={
            "fields": [
                {"key": "approver", "value": "admin,dba1,dba2"},
                {"key": "approval_result", "value": "true"},
            ]
        },
    )

    yield ticket, flow
    flow.delete()
    ticket.delete()


@pytest.fixture
def init_running_ticket_with_flow(test_ticket_bk_biz_id):
    """创建正在运行的单据及关联 flow，用于 operate_flow 和 revoke_ticket 测试"""
    ticket = Ticket.objects.create(
        id=2004,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test running ticket for handler",
        details={"nodes": {}},
        group=TicketType.MYSQL_HA_APPLY.value,
    )
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="MySQL部署流程",
        status=TicketFlowStatus.RUNNING,
    )
    yield ticket, flow
    flow.delete()
    ticket.delete()


@pytest.fixture
def init_todo(test_ticket_bk_biz_id):
    """创建带有待办的单据"""
    ticket = Ticket.objects.create(
        id=2005,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="test ticket with todo for handler",
        details={"nodes": {}},
        group=TicketType.MYSQL_HA_APPLY.value,
    )
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="待办流程",
        status=TicketFlowStatus.RUNNING,
    )
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
def init_global_flow_config():
    """创建全局单据流程配置"""
    config = TicketFlowsConfig.objects.create(
        bk_biz_id=PLAT_BIZ_ID,
        group=DBType.MySQL.value,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        editable=True,
        configs={
            FlowTypeConfig.NEED_ITSM: False,
            FlowTypeConfig.NEED_MANUAL_CONFIRM: False,
            FlowTypeConfig.EXPIRE_CONFIG: {"enable": False},
        },
        creator="admin",
        updater="admin",
    )
    yield config
    config.delete()


class TestTicketHandlerAddRelatedObject:
    """测试 TicketHandler.add_related_object 补充关联对象"""

    def test_add_related_object_with_clusters(self, init_ticket_with_clusters):
        """测试补充关联对象 - 集群类型"""
        ticket = init_ticket_with_clusters
        ticket_data = [{"id": ticket.id}]

        result = TicketHandler.add_related_object(ticket_data)

        assert len(result) == 1
        assert result[0]["related_object"]["title"] == "集群"
        assert "cluster100.db.com" in result[0]["related_object"]["objects"]
        assert "cluster200.db.com" in result[0]["related_object"]["objects"]

    def test_add_related_object_with_instances(self, init_ticket_with_instances):
        """测试补充关联对象 - 实例类型"""
        ticket = init_ticket_with_instances
        ticket_data = [{"id": ticket.id}]

        result = TicketHandler.add_related_object(ticket_data)

        assert len(result) == 1
        assert result[0]["related_object"]["title"] == "实例"
        assert f"{cc.NORMAL_IP}:3306" in result[0]["related_object"]["objects"]
        assert f"{cc.NORMAL_IP2}:3306" in result[0]["related_object"]["objects"]

    def test_add_related_object_empty_list(self):
        """测试补充关联对象 - 空列表"""
        result = TicketHandler.add_related_object([])

        assert result == []

    def test_add_related_object_no_clusters_no_instances(self, test_mysql_single_apply_ticket):
        """测试补充关联对象 - 既无集群也无实例"""
        ticket = test_mysql_single_apply_ticket
        ticket_data = [{"id": ticket.id}]

        result = TicketHandler.add_related_object(ticket_data)

        assert len(result) == 1
        assert "related_object" not in result[0]


class TestTicketHandlerFastCreateCloudComponent:
    """测试 TicketHandler.fast_create_cloud_component_method 快速部署云区域组件"""

    @patch("backend.ticket.handler.Ticket.create_ticket")
    @patch("backend.ticket.handler.HostHandler.details")
    def test_fast_create_cloud_component_method(self, mock_host_details, mock_create_ticket, test_ticket_bk_biz_id):
        """测试快速部署云区域组件 - 正常流程"""
        mock_host_details.return_value = [
            {
                "host_id": 1,
                "ip": cc.NORMAL_IP,
                "cloud_id": 0,
                "bk_host_outerip": cc.NORMAL_IP,
                "bk_idc_id": 1,
                "bk_idc_city_name": "SZ",
            },
            {
                "host_id": 2,
                "ip": cc.NORMAL_IP2,
                "cloud_id": 0,
                "bk_host_outerip": cc.NORMAL_IP2,
                "bk_idc_id": 2,
                "bk_idc_city_name": "SZ",
            },
        ]

        TicketHandler.fast_create_cloud_component_method(
            bk_biz_id=test_ticket_bk_biz_id,
            bk_cloud_id=1,
            ips=[cc.NORMAL_IP, cc.NORMAL_IP2],
        )

        mock_host_details.assert_called_once()
        mock_create_ticket.assert_called_once()
        create_kwargs = mock_create_ticket.call_args.kwargs
        assert create_kwargs["ticket_type"] == TicketType.CLOUD_SERVICE_APPLY
        assert create_kwargs["bk_biz_id"] == test_ticket_bk_biz_id
        assert create_kwargs["details"]["bk_cloud_id"] == 1
        assert "dns" in create_kwargs["details"]
        assert "nginx" in create_kwargs["details"]
        assert "drs" in create_kwargs["details"]
        assert "dbha" in create_kwargs["details"]

    @patch("backend.ticket.handler.Ticket.create_ticket")
    @patch("backend.ticket.handler.HostHandler.details")
    def test_fast_create_cloud_component_method_custom_user(
        self, mock_host_details, mock_create_ticket, test_ticket_bk_biz_id
    ):
        """测试快速部署云区域组件 - 自定义用户"""
        mock_host_details.return_value = [
            {
                "host_id": 1,
                "ip": cc.NORMAL_IP,
                "cloud_id": 0,
                "bk_host_outerip": "",
                "bk_idc_id": None,
                "bk_idc_city_name": "",
            },
            {
                "host_id": 2,
                "ip": cc.NORMAL_IP2,
                "cloud_id": 0,
                "bk_host_outerip": "",
                "bk_idc_id": None,
                "bk_idc_city_name": "",
            },
        ]

        TicketHandler.fast_create_cloud_component_method(
            bk_biz_id=test_ticket_bk_biz_id,
            bk_cloud_id=0,
            ips=[cc.NORMAL_IP, cc.NORMAL_IP2],
            user="custom_user",
        )

        create_kwargs = mock_create_ticket.call_args.kwargs
        assert create_kwargs["creator"] == "custom_user"
        # 当 bk_host_outerip 为空时，应使用 ip 作为 bk_outer_ip
        nginx_info = create_kwargs["details"]["nginx"]["host_infos"][0]
        assert nginx_info["bk_outer_ip"] == cc.NORMAL_IP2


class TestTicketHandlerItsmOperations:
    """测试 TicketHandler ITSM 相关方法"""

    def test_get_itsm_approvers(self, init_itsm_flow):
        """测试获取 ITSM 审批人列表"""
        _, flow = init_itsm_flow

        approvers = TicketHandler.get_itsm_approvers(flow)

        assert approvers == ["admin", "dba1", "dba2"]

    def test_get_itsm_approvers_non_itsm_flow(self, init_running_ticket_with_flow):
        """测试获取审批人 - 非 ITSM 类型的 flow 返回空列表"""
        _, flow = init_running_ticket_with_flow

        approvers = TicketHandler.get_itsm_approvers(flow)

        assert approvers == []

    def test_get_itsm_todo_operators_normal(self, init_itsm_flow):
        """测试获取 ITSM 待办处理人 - 普通单据"""
        _, flow = init_itsm_flow

        operators, helpers = TicketHandler.get_itsm_todo_operators(flow)

        # 普通单据：首人是处理人，其余是协助者
        assert operators == ["admin"]
        assert helpers == ["dba1", "dba2"]

    def test_get_itsm_todo_operators_special_ticket(self, init_itsm_flow):
        """测试获取 ITSM 待办处理人 - 特殊审批单据所有人均为处理者"""
        ticket, flow = init_itsm_flow
        # 将单据类型修改为特殊审批单据
        if SPECIAL_APPROVE_TICKETS:
            ticket.ticket_type = SPECIAL_APPROVE_TICKETS[0]
            ticket.save()

            operators, helpers = TicketHandler.get_itsm_todo_operators(flow)

            assert operators == ["admin", "dba1", "dba2"]
            assert helpers == []

    @patch("backend.ticket.handler.SystemSettings.get_setting_value")
    def test_get_itsm_fields(self, mock_get_setting):
        """测试获取 ITSM 审批字段"""
        mock_get_setting.side_effect = [
            {"0": "approval_key_0", "1": "approval_key_1"},
            {"0": "remark_key_0", "1": "remark_key_1"},
        ]

        approval_key, remark_key = TicketHandler.get_itsm_fields(TicketType.MYSQL_SINGLE_APPLY)

        assert mock_get_setting.call_count == 2

    @patch("backend.ticket.handler.ItsmApi.operate_ticket")
    @patch("backend.ticket.handler.ItsmApi.operate_node")
    @patch("backend.ticket.handler.ItsmApi.get_ticket_info")
    @patch("backend.ticket.handler.TicketHandler.get_itsm_fields")
    def test_operate_itsm_ticket_transition(
        self, mock_get_fields, mock_get_info, mock_operate_node, mock_operate_ticket, init_itsm_flow
    ):
        """测试操作 ITSM 单据 - 审批通过"""
        ticket, flow = init_itsm_flow
        mock_get_info.return_value = {
            "current_steps": [{"state_id": 1}],
        }
        mock_get_fields.return_value = ("approval_key", "remark_key")

        sn = TicketHandler.operate_itsm_ticket(
            ticket_id=ticket.id,
            action=OperateNodeActionType.TRANSITION,
            operator="admin",
            is_approved=True,
        )

        assert sn == flow.flow_obj_id
        mock_operate_node.assert_called_once()
        call_kwargs = mock_operate_node.call_args[0][0]
        assert call_kwargs["sn"] == flow.flow_obj_id
        assert call_kwargs["operator"] == "admin"
        assert call_kwargs["state_id"] == 1
        mock_operate_ticket.assert_not_called()

    @patch("backend.ticket.handler.ItsmApi.operate_ticket")
    @patch("backend.ticket.handler.ItsmApi.operate_node")
    @patch("backend.ticket.handler.ItsmApi.get_ticket_info")
    def test_operate_itsm_ticket_terminate(
        self, mock_get_info, mock_operate_node, mock_operate_ticket, init_itsm_flow
    ):
        """测试操作 ITSM 单据 - 终止"""
        ticket, flow = init_itsm_flow
        mock_get_info.return_value = {
            "current_steps": [{"state_id": 1}],
        }

        sn = TicketHandler.operate_itsm_ticket(
            ticket_id=ticket.id,
            action=OperateNodeActionType.TERMINATE,
            operator="admin",
        )

        assert sn == flow.flow_obj_id
        mock_operate_ticket.assert_called_once()
        mock_operate_node.assert_not_called()

    @patch("backend.ticket.handler.ItsmApi.operate_ticket")
    @patch("backend.ticket.handler.ItsmApi.operate_node")
    @patch("backend.ticket.handler.ItsmApi.get_ticket_info")
    def test_operate_itsm_ticket_withdraw(self, mock_get_info, mock_operate_node, mock_operate_ticket, init_itsm_flow):
        """测试操作 ITSM 单据 - 撤销"""
        ticket, flow = init_itsm_flow
        mock_get_info.return_value = {
            "current_steps": [{"state_id": 1}],
        }

        sn = TicketHandler.operate_itsm_ticket(
            ticket_id=ticket.id,
            action=OperateNodeActionType.WITHDRAW,
            operator="admin",
        )

        assert sn == flow.flow_obj_id
        mock_operate_ticket.assert_called_once()
        mock_operate_node.assert_not_called()

    @patch("backend.ticket.handler.ItsmApi.operate_node")
    @patch("backend.ticket.handler.ItsmApi.get_ticket_info")
    def test_operate_itsm_ticket_deliver(self, mock_get_info, mock_operate_node, init_itsm_flow):
        """测试操作 ITSM 单据 - 转单"""
        ticket, flow = init_itsm_flow
        mock_get_info.return_value = {
            "current_steps": [{"state_id": 1}],
        }

        sn = TicketHandler.operate_itsm_ticket(
            ticket_id=ticket.id,
            action=OperateNodeActionType.DELIVER,
            operator="admin",
            processors="dba_new",
        )

        assert sn == flow.flow_obj_id
        mock_operate_node.assert_called_once()
        call_kwargs = mock_operate_node.call_args[0][0]
        assert call_kwargs["processors"] == "dba_new"
        assert call_kwargs["processors_type"] == "PERSON"
        assert call_kwargs["state_id"] == 1

    @patch("backend.ticket.handler.ItsmApi.get_ticket_info")
    def test_operate_itsm_ticket_no_current_steps(self, mock_get_info, init_itsm_flow):
        """测试操作 ITSM 单据 - 当前无进行中步骤时直接返回"""
        ticket, _ = init_itsm_flow
        mock_get_info.return_value = {"current_steps": []}

        result = TicketHandler.operate_itsm_ticket(
            ticket_id=ticket.id,
            action=OperateNodeActionType.TRANSITION,
            operator="admin",
            is_approved=True,
        )

        assert result is None


class TestTicketHandlerFlowOperations:
    """测试 TicketHandler 流程操作方法"""

    @patch("backend.ticket.handler.TicketFlowManager")
    def test_operate_flow(self, mock_flow_manager_cls, init_running_ticket_with_flow):
        """测试进行 flow 操作"""
        ticket, flow = init_running_ticket_with_flow
        mock_flow_cls = MagicMock()
        mock_flow_instance = MagicMock()
        mock_flow_cls.return_value = mock_flow_instance
        mock_manager = MagicMock()
        mock_manager.get_ticket_flow_cls.return_value = mock_flow_cls
        mock_flow_manager_cls.return_value = mock_manager

        TicketHandler.operate_flow(ticket.id, flow.id, "retry")

        mock_flow_manager_cls.assert_called_once_with(ticket=ticket)
        mock_manager.get_ticket_flow_cls.assert_called_once_with(flow.flow_type)
        mock_flow_instance.retry.assert_called_once()

    @patch("backend.ticket.handler.TicketHandler.operate_flow")
    def test_revoke_ticket(self, mock_operate_flow, init_running_ticket_with_flow):
        """测试终止单据"""
        ticket, flow = init_running_ticket_with_flow

        TicketHandler.revoke_ticket(
            ticket_ids=[ticket.id],
            operator="admin",
            remark="测试终止",
        )

        mock_operate_flow.assert_called_once_with(ticket.id, flow.id, func="revoke", operator="admin", remark="测试终止")

    @patch("backend.ticket.handler.TicketHandler.operate_flow")
    def test_revoke_ticket_no_running_flows(self, mock_operate_flow, test_ticket_bk_biz_id):
        """测试终止单据 - 没有运行中的 flow"""
        ticket = Ticket.objects.create(
            id=2010,
            bk_biz_id=test_ticket_bk_biz_id,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.SUCCEEDED,
            creator="admin",
            updater="admin",
            remark="test succeeded ticket",
            details={"nodes": {}},
            group=TicketType.MYSQL_SINGLE_APPLY.value,
        )
        # 创建一个已完成的 flow
        flow = Flow.objects.create(
            ticket=ticket,
            flow_type=FlowType.INNER_FLOW,
            flow_alias="已完成流程",
            status=TicketFlowStatus.SUCCEEDED,
        )

        try:
            TicketHandler.revoke_ticket(
                ticket_ids=[ticket.id],
                operator="admin",
                remark="尝试终止已完成单据",
            )

            mock_operate_flow.assert_not_called()
        finally:
            flow.delete()
            ticket.delete()

    @patch("backend.ticket.handler.TicketHandler.operate_flow")
    def test_revoke_ticket_multiple(self, mock_operate_flow, test_ticket_bk_biz_id):
        """测试批量终止单据"""
        tickets = []
        flows = []
        for i in range(2):
            ticket = Ticket.objects.create(
                id=2020 + i,
                bk_biz_id=test_ticket_bk_biz_id,
                ticket_type=TicketType.MYSQL_HA_APPLY,
                status=TicketStatus.RUNNING,
                creator="admin",
                updater="admin",
                remark=f"test revoke multiple {i}",
                details={"nodes": {}},
                group=TicketType.MYSQL_HA_APPLY.value,
            )
            flow = Flow.objects.create(
                ticket=ticket,
                flow_type=FlowType.INNER_FLOW,
                flow_alias=f"流程{i}",
                status=TicketFlowStatus.RUNNING,
            )
            tickets.append(ticket)
            flows.append(flow)

        try:
            TicketHandler.revoke_ticket(
                ticket_ids=[t.id for t in tickets],
                operator="admin",
                remark="批量终止",
            )

            assert mock_operate_flow.call_count == 2
        finally:
            for f in flows:
                f.delete()
            for t in tickets:
                t.delete()


class TestTicketHandlerTodoOperations:
    """测试 TicketHandler 待办操作方法"""

    @patch("backend.ticket.handler.TodoActorFactory.actor")
    def test_batch_process_todo_approve(self, mock_actor, init_todo):
        """测试批量处理待办 - 审批动作"""
        _, _, todo = init_todo
        mock_actor_instance = MagicMock()
        mock_actor.return_value = mock_actor_instance

        operations = [{"todo_id": todo.id, "params": {"message": "approved"}}]

        result = TicketHandler.batch_process_todo(
            user="admin",
            action=TodoActionType.APPROVE,
            operations=operations,
        )

        # 验证返回的是真实的 TodoSerializer 序列化结果（不 mock 序列化器）
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == todo.id
        assert result[0]["name"] == "人工确认"
        assert result[0]["type"] == TodoType.INNER_APPROVE
        assert result[0]["status"] == TodoStatus.TODO
        mock_actor.assert_called_once()
        mock_actor_instance.process.assert_called_once_with("admin", TodoActionType.APPROVE, {"message": "approved"})

    @patch("backend.ticket.handler.TodoActorFactory.actor")
    def test_batch_process_todo_deliver(self, mock_actor, init_todo):
        """测试批量处理待办 - 转单动作"""
        _, _, todo = init_todo
        mock_actor_instance = MagicMock()
        mock_actor.return_value = mock_actor_instance

        operations = [{"todo_id": todo.id, "params": {"processors": ["dba_new"], "remark": "请处理"}}]

        result = TicketHandler.batch_process_todo(
            user="admin",
            action=TodoActionType.DELIVER,
            operations=operations,
        )

        # 验证返回的是真实的 TodoSerializer 序列化结果（不 mock 序列化器）
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == todo.id
        assert result[0]["name"] == "人工确认"
        assert result[0]["type"] == TodoType.INNER_APPROVE
        assert result[0]["status"] == TodoStatus.TODO
        mock_actor.assert_called_once()
        mock_actor_instance.deliver.assert_called_once_with(
            "admin", TodoActionType.DELIVER, {"processors": ["dba_new"], "remark": "请处理"}
        )

    @patch("backend.ticket.handler.TicketHandler.batch_process_todo")
    def test_batch_process_ticket(self, mock_batch_todo, init_todo):
        """测试批量操作单据的待办"""
        ticket, flow, todo = init_todo
        # init_todo 的 todo type 为 INNER_APPROVE，会被 exclude 过滤
        # 因此传递给 batch_process_todo 的 operations 应为空列表
        mock_batch_todo.return_value = []

        result = TicketHandler.batch_process_ticket(
            username="admin",
            action=TodoActionType.APPROVE,
            ticket_ids=[ticket.id],
            params={"message": "batch approved"},
        )

        # INNER_APPROVE 类型被排除，operations 为空，返回值也应为空
        assert result == []
        mock_batch_todo.assert_called_once_with(user="admin", action=TodoActionType.APPROVE, operations=[])

    @patch("backend.ticket.handler.TicketHandler.batch_process_todo")
    def test_batch_process_ticket_no_running_todo(self, mock_batch_todo, test_ticket_bk_biz_id):
        """测试批量操作单据的待办 - 无运行中待办"""
        ticket = Ticket.objects.create(
            id=2030,
            bk_biz_id=test_ticket_bk_biz_id,
            ticket_type=TicketType.MYSQL_HA_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="test no todo",
            details={"nodes": {}},
            group=TicketType.MYSQL_HA_APPLY.value,
        )
        mock_batch_todo.return_value = []

        try:
            result = TicketHandler.batch_process_ticket(
                username="admin",
                action=TodoActionType.APPROVE,
                ticket_ids=[ticket.id],
                params={},
            )

            assert result == []
            # 没有运行中待办，operations 为空列表
            mock_batch_todo.assert_called_once_with(user="admin", action=TodoActionType.APPROVE, operations=[])
        finally:
            ticket.delete()


class TestTicketHandlerFlowConfig:
    """测试 TicketHandler 单据流程配置方法"""

    @patch("backend.ticket.handler.BuilderFactory")
    def test_ticket_flow_config_init(self, mock_builder_factory):
        """测试初始化单据配置"""
        # 模拟 BuilderFactory.registry，包含一个已存在类型和一个新增类型
        existing_type = TicketType.MYSQL_SINGLE_APPLY.value

        mock_flow_class = MagicMock()
        mock_flow_class.group = DBType.MySQL.value
        mock_flow_class.editable = True
        mock_flow_class.default_need_manual_confirm = False
        mock_flow_class.default_need_itsm = False
        mock_flow_class.default_expire_config = {"enable": False}

        mock_builder_factory.registry = {existing_type: mock_flow_class}

        # 先清理可能存在的配置
        TicketFlowsConfig.objects.filter(ticket_type=existing_type).delete()

        TicketHandler.ticket_flow_config_init()

        # 验证新类型的配置被创建
        config = TicketFlowsConfig.objects.filter(ticket_type=existing_type).first()
        assert config is not None
        assert config.group == DBType.MySQL.value

        # 清理
        TicketFlowsConfig.objects.filter(ticket_type=existing_type, bk_biz_id=PLAT_BIZ_ID).delete()

    def test_create_ticket_flow_config_platform_level_raises(self, init_global_flow_config):
        """测试创建单据流程配置 - 平台级别不允许新增"""
        # 清理 ticket_flow_config_init 测试可能遗留的同类型全局配置
        TicketFlowsConfig.objects.filter(
            bk_biz_id=PLAT_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        ).exclude(id=init_global_flow_config.id).delete()
        with pytest.raises(TicketFlowsConfigException):
            TicketHandler.create_ticket_flow_config(
                bk_biz_id=0,
                cluster_ids=[],
                ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
                configs={
                    "need_itsm": True,
                    "need_manual_confirm": False,
                },
                operator="admin",
                remark="test",
            )

    def test_create_ticket_flow_config_biz_level(self, test_ticket_bk_biz_id, init_global_flow_config):
        """测试创建业务级别流程配置"""
        # 清理同类型全局配置残留，确保 get() 不会匹配多条
        TicketFlowsConfig.objects.filter(
            bk_biz_id=PLAT_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        ).exclude(id=init_global_flow_config.id).delete()
        configs = {
            "need_itsm": True,
            "need_manual_confirm": False,
            "expire_config": {"enable": False},
        }

        try:
            TicketHandler.create_ticket_flow_config(
                bk_biz_id=test_ticket_bk_biz_id,
                cluster_ids=[],
                ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
                configs=configs,
                operator="admin",
                remark="test create biz config",
            )

            biz_config = TicketFlowsConfig.objects.filter(
                bk_biz_id=test_ticket_bk_biz_id,
                ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
            ).first()
            assert biz_config is not None
            assert biz_config.configs["need_itsm"] is True
        finally:
            TicketFlowsConfig.objects.filter(
                bk_biz_id=test_ticket_bk_biz_id,
                ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
            ).delete()

    def test_create_ticket_flow_config_duplicate_biz_raises(self, test_ticket_bk_biz_id, init_global_flow_config):
        """测试创建业务级别流程配置 - 重复创建抛出异常"""
        # 清理同类型全局配置残留，确保 get() 不会匹配多条
        TicketFlowsConfig.objects.filter(
            bk_biz_id=PLAT_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        ).exclude(id=init_global_flow_config.id).delete()
        configs = {
            "need_itsm": True,
            "need_manual_confirm": False,
            "expire_config": {"enable": False},
        }

        try:
            # 第一次创建
            TicketHandler.create_ticket_flow_config(
                bk_biz_id=test_ticket_bk_biz_id,
                cluster_ids=[],
                ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
                configs=configs,
                operator="admin",
                remark="first create",
            )

            # 第二次创建应抛出异常
            with pytest.raises(TicketFlowsConfigException):
                TicketHandler.create_ticket_flow_config(
                    bk_biz_id=test_ticket_bk_biz_id,
                    cluster_ids=[],
                    ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
                    configs=configs,
                    operator="admin",
                    remark="duplicate create",
                )
        finally:
            TicketFlowsConfig.objects.filter(
                bk_biz_id=test_ticket_bk_biz_id,
                ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
            ).delete()

    def test_update_ticket_flow_config_global(self, init_global_flow_config):
        """测试更新全局单据流程配置"""
        new_configs = {
            "need_itsm": True,
            "need_manual_confirm": True,
            "expire_config": {"enable": True},
        }

        TicketHandler.update_ticket_flow_config(
            bk_biz_id=0,
            cluster_ids=[],
            ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
            configs=new_configs,
            config_ids=[],
            operator="admin",
            remark="test update global",
        )

        init_global_flow_config.refresh_from_db()
        assert init_global_flow_config.configs["need_itsm"] is True
        assert init_global_flow_config.configs["need_manual_confirm"] is True

    @patch("backend.ticket.handler.TicketHandler.create_ticket_flow_config")
    def test_update_ticket_flow_config_biz_level(self, mock_create, test_ticket_bk_biz_id, init_global_flow_config):
        """测试更新业务级别单据流程配置"""
        # 先创建业务级别配置
        biz_config = TicketFlowsConfig.objects.create(
            bk_biz_id=test_ticket_bk_biz_id,
            group=DBType.MySQL.value,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
            editable=True,
            configs={"need_itsm": True, "need_manual_confirm": False},
            creator="admin",
            updater="admin",
        )

        try:
            new_configs = {
                "need_itsm": False,
                "need_manual_confirm": False,
                "expire_config": {"enable": False},
            }

            TicketHandler.update_ticket_flow_config(
                bk_biz_id=test_ticket_bk_biz_id,
                cluster_ids=[],
                ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
                configs=new_configs,
                config_ids=[biz_config.id],
                operator="admin",
                remark="test update biz",
            )

            # 原配置应被删除
            assert not TicketFlowsConfig.objects.filter(id=biz_config.id).exists()
            # create_ticket_flow_config 应被调用以创建新配置
            mock_create.assert_called_once()
        finally:
            TicketFlowsConfig.objects.filter(
                bk_biz_id=test_ticket_bk_biz_id,
                ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
            ).delete()

    @patch("backend.ticket.handler.BuilderFactory")
    def test_query_ticket_flows_describe(self, mock_builder_factory, test_ticket_bk_biz_id, init_global_flow_config):
        """测试查询单据流程描述"""
        # 清理其他测试可能遗留的同类型配置，避免查询出多条结果
        TicketFlowsConfig.objects.filter(
            bk_biz_id__in=[test_ticket_bk_biz_id, PLAT_BIZ_ID],
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        ).exclude(id=init_global_flow_config.id).delete()

        mock_flow_class = MagicMock()
        mock_flow_class.describe_ticket_flows.return_value = [
            {"flow_type": "itsm", "flow_type_display": "审批"},
            {"flow_type": "inner_flow", "flow_type_display": "执行"},
        ]
        mock_builder_factory.registry = {TicketType.MYSQL_SINGLE_APPLY.value: mock_flow_class}

        result = TicketHandler.query_ticket_flows_describe(
            bk_biz_id=test_ticket_bk_biz_id,
            db_type=DBType.MySQL.value,
            ticket_types=[TicketType.MYSQL_SINGLE_APPLY.value],
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert "flow_desc" in result[0]
        assert isinstance(result[0]["flow_desc"], list)
        assert result[0]["ticket_type"] == TicketType.MYSQL_SINGLE_APPLY.value
