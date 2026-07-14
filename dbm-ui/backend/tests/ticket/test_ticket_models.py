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
from django.test.testcases import TransactionTestCase

from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc
from backend.ticket.constants import (
    FlowContext,
    FlowErrCode,
    FlowType,
    TicketFlowStatus,
    TicketStatus,
    TicketType,
    TodoStatus,
    TodoType,
)
from backend.ticket.models import Todo
from backend.ticket.models.ticket import (
    ClusterOperateRecord,
    Flow,
    FlowSummary,
    InstanceOperateRecord,
    Ticket,
    TicketFlowsConfig,
)

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")


# ==================== Fixtures ====================


@pytest.fixture
def base_ticket(db):
    """创建基础测试单据"""
    ticket = Ticket.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.PENDING,
        creator="admin",
        updater="admin",
        remark="模型层测试单据",
        details={"nodes": {"backend": []}, "ip_source": "manual_input"},
        group=DBType.MySQL.value,
    )
    yield ticket
    ticket.delete()


@pytest.fixture
def running_ticket(db):
    """创建运行中的测试单据"""
    ticket = Ticket.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="运行中测试单据",
        details={"nodes": {}, "clusters": {}},
        group=DBType.MySQL.value,
    )
    yield ticket
    ticket.delete()


@pytest.fixture
def base_flow(base_ticket):
    """创建基础测试流程"""
    flow = Flow.objects.create(
        ticket=base_ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="测试内部流程",
        status=TicketFlowStatus.PENDING,
        details={},
    )
    yield flow
    flow.delete()


@pytest.fixture
def running_flow(running_ticket):
    """创建运行中的测试流程"""
    flow = Flow.objects.create(
        ticket=running_ticket,
        flow_type=FlowType.INNER_FLOW,
        flow_alias="运行中内部流程",
        flow_obj_id="test_root_id_001",
        status=TicketFlowStatus.RUNNING,
        details={"task_id": "initial"},
    )
    yield flow
    flow.delete()


@pytest.fixture
def cluster_operate_record(running_ticket, running_flow):
    """创建集群操作记录"""
    record = ClusterOperateRecord.objects.create(
        cluster_id=3001,
        flow=running_flow,
        ticket=running_ticket,
        creator="admin",
        updater="admin",
    )
    yield record
    record.delete()


@pytest.fixture
def instance_operate_record(running_ticket, running_flow):
    """创建实例操作记录"""
    record = InstanceOperateRecord.objects.create(
        instance_id=f"{cc.NORMAL_IP}:3306",
        flow=running_flow,
        ticket=running_ticket,
        creator="admin",
        updater="admin",
    )
    yield record
    record.delete()


@pytest.fixture
def ticket_flows_config(db):
    """创建单据流程配置"""
    # 先清理可能已存在的同类型平台配置，避免 MultipleObjectsReturned
    TicketFlowsConfig.objects.filter(
        bk_biz_id=PLAT_BIZ_ID,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
    ).delete()
    config = TicketFlowsConfig.objects.create(
        bk_biz_id=PLAT_BIZ_ID,
        group=DBType.MySQL.value,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        editable=True,
        configs={"need_itsm": False, "need_manual_confirm": False},
        creator="admin",
        updater="admin",
    )
    yield config
    config.delete()


# ==================== TestFlow ====================


class TestFlow:
    """测试 Flow 模型"""

    def test_create_and_query(self, base_flow):
        """测试创建和查询"""
        assert Flow.objects.filter(id=base_flow.id).exists()
        saved = Flow.objects.get(id=base_flow.id)
        assert saved.flow_type == FlowType.INNER_FLOW
        assert saved.status == TicketFlowStatus.PENDING

    def test_update_details(self, base_flow):
        """测试更新流程详情"""
        result = base_flow.update_details(task_id="abc123", extra_info="test")

        assert result == {"task_id": "abc123", "extra_info": "test"}
        base_flow.refresh_from_db()
        assert base_flow.details["task_id"] == "abc123"
        assert base_flow.details["extra_info"] == "test"

    def test_update_status(self, base_flow):
        """测试更新流程状态"""
        result = base_flow.update_status(TicketFlowStatus.RUNNING)

        assert result == TicketFlowStatus.RUNNING
        base_flow.refresh_from_db()
        assert base_flow.status == TicketFlowStatus.RUNNING

    def test_update_status_same_value(self, base_flow):
        """测试更新流程状态 - 状态相同时不触发保存"""
        result = base_flow.update_status(TicketFlowStatus.PENDING)

        assert result == TicketFlowStatus.PENDING

    def test_update_context(self, base_flow):
        """测试更新流程上下文"""
        result = base_flow.update_context(expire_time=7, remark="测试备注")

        assert result["expire_time"] == 7
        assert result["remark"] == "测试备注"
        base_flow.refresh_from_db()
        assert base_flow.context["expire_time"] == 7

    def test_flow_output_empty(self, base_flow):
        """测试 flow_output - 无 __flow_output 时返回空字典"""
        result = base_flow.flow_output
        assert result == {}

    def test_flow_output_non_sensitive(self, base_flow):
        """测试 flow_output - 非敏感数据直接返回"""
        base_flow.details = {"__flow_output": {"data": {"key": "value"}, "is_sensitive": False}}
        base_flow.save()

        result = base_flow.flow_output
        assert result == {"key": "value"}

    def test_flow_output_sensitive(self, base_flow):
        """测试 flow_output - 敏感数据需解密"""
        base_flow.details = {"__flow_output": {"data": "encrypted_content", "is_sensitive": True}}
        base_flow.save()

        with patch(
            "backend.ticket.models.ticket.AsymmetricHandler.decrypt",
            return_value='{"secret": "decrypted_value"}',
        ):
            result = base_flow.flow_output

        assert result == {"secret": "decrypted_value"}

    def test_output_data_no_summary(self, base_flow):
        """测试 output_data - 无 FlowSummary 时返回空列表"""
        result = base_flow.output_data
        assert result == []

    def test_output_data_with_summary(self, base_flow):
        """测试 output_data - 有 FlowSummary 时返回摘要数据"""
        summary = FlowSummary.objects.create(flow=base_flow, summary=[{"step": "deploy", "status": "success"}])

        # 重新查询以加载关联
        flow = Flow.objects.get(id=base_flow.id)
        result = flow.output_data
        assert result == [{"step": "deploy", "status": "success"}]
        summary.delete()

    def test_get_inner_controller_func_not_inner_flow(self, base_flow):
        """测试 get_inner_controller_func - 非 INNER_FLOW 返回 None"""
        base_flow.flow_type = FlowType.BK_ITSM
        base_flow.save()

        result = base_flow.get_inner_controller_func()
        assert result is None

    def test_get_inner_controller_func_success(self, base_flow):
        """测试 get_inner_controller_func - 正常返回控制器函数"""
        mock_func = MagicMock()
        mock_controller_inst = MagicMock()
        mock_controller_inst.execute = mock_func
        mock_controller_cls = MagicMock(return_value=mock_controller_inst)
        mock_module = MagicMock()
        mock_module.FakeController = mock_controller_cls

        base_flow.flow_type = FlowType.INNER_FLOW
        base_flow.flow_obj_id = "test_root_id"
        base_flow.details = {
            "controller_info": {
                "module": "backend.flow.engine.controller.fake",
                "class_name": "FakeController",
                "func_name": "execute",
            },
            "ticket_data": {"key": "value"},
        }
        base_flow.save()

        with patch(
            "backend.ticket.models.ticket.importlib.import_module",
            return_value=mock_module,
        ):
            result = base_flow.get_inner_controller_func()

        assert result == mock_func


# ==================== TestFlowSummary ====================


class TestFlowSummary:
    """测试 FlowSummary 模型"""

    def test_create_and_query(self, base_flow):
        """测试创建和查询"""
        summary = FlowSummary.objects.create(flow=base_flow, summary=[{"key": "value"}])

        assert FlowSummary.objects.filter(flow=base_flow).exists()
        saved = FlowSummary.objects.get(flow=base_flow)
        assert saved.summary == [{"key": "value"}]
        summary.delete()

    def test_default_summary(self, base_flow):
        """测试默认摘要为空列表"""
        summary = FlowSummary.objects.create(flow=base_flow)

        saved = FlowSummary.objects.get(flow=base_flow)
        assert saved.summary == []
        summary.delete()


# ==================== TestTicket ====================


class TestTicket:
    """测试 Ticket 模型"""

    def test_create_and_query(self, base_ticket):
        """测试创建和查询"""
        assert Ticket.objects.filter(id=base_ticket.id).exists()
        saved = Ticket.objects.get(id=base_ticket.id)
        assert saved.bk_biz_id == constant.BK_BIZ_ID
        assert saved.ticket_type == TicketType.MYSQL_SINGLE_APPLY
        assert saved.status == TicketStatus.PENDING

    def test_url_property(self, base_ticket):
        """测试 url 属性"""
        with patch("backend.ticket.models.ticket.env") as mock_env:
            mock_env.BK_SAAS_HOST = "https://bk.example.com"
            result = base_ticket.url

        assert result == f"https://bk.example.com/ticket/{base_ticket.id}"

    def test_iframe_url_property(self, base_ticket):
        """测试 iframe_url 属性"""
        with patch("backend.ticket.models.ticket.env") as mock_env:
            mock_env.BK_SAAS_HOST = "https://bk.example.com"
            result = base_ticket.iframe_url

        assert result == f"https://bk.example.com/ticket/{base_ticket.id}"

    def test_helpers_property(self, base_ticket):
        """测试 helpers 属性 - 有配置时返回协助人列表"""
        base_ticket.config = {"helpers": ["dba1", "dba2"]}
        base_ticket.save()

        result = base_ticket.helpers
        assert result == ["dba1", "dba2"]

    def test_helpers_property_empty(self, base_ticket):
        """测试 helpers 属性 - 无配置时返回空列表"""
        base_ticket.config = {}
        base_ticket.save()

        result = base_ticket.helpers
        assert result == []

    def test_helpers_property_none_config(self, base_ticket):
        """测试 helpers 属性 - config 为 None 时返回空列表"""
        base_ticket.config = None
        base_ticket.save()

        result = base_ticket.helpers
        assert result == []

    def test_context_property(self, base_ticket):
        """测试 context 属性"""
        base_ticket.config = {"context": {"flow_id": 123}}
        base_ticket.save()

        result = base_ticket.context
        assert result == {"flow_id": 123}

    def test_msg_config_property(self, base_ticket):
        """测试 msg_config 属性"""
        base_ticket.config = {"send_msg_config": {"type": "email"}}
        base_ticket.save()

        result = base_ticket.msg_config
        assert result == {"type": "email"}

    def test_set_status(self, base_ticket):
        """测试设置状态"""
        base_ticket.set_status(TicketStatus.RUNNING)

        base_ticket.refresh_from_db()
        assert base_ticket.status == TicketStatus.RUNNING

    def test_get_cost_time_pending(self, base_ticket):
        """测试获取耗时 - 待处理状态"""
        base_ticket.status = TicketStatus.PENDING
        base_ticket.save()

        result = base_ticket.get_cost_time()
        assert isinstance(result, int)

    def test_get_cost_time_succeeded(self, base_ticket):
        """测试获取耗时 - 已完成状态"""
        base_ticket.status = TicketStatus.SUCCEEDED
        base_ticket.save()

        result = base_ticket.get_cost_time()
        assert isinstance(result, int)

    def test_get_terminate_reason_not_terminated(self, base_ticket):
        """测试获取终止原因 - 非终止状态返回空字符串"""
        result = base_ticket.get_terminate_reason()
        assert result == ""

    def test_get_terminate_reason_system_terminated(self, base_ticket):
        """测试获取终止原因 - 系统终止"""
        base_ticket.status = TicketStatus.TERMINATED
        base_ticket.save()

        flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.TERMINATED,
            err_code=FlowErrCode.SYSTEM_TERMINATED_ERROR,
            context={FlowContext.EXPIRE_TIME: 30},
            details={},
        )

        result = base_ticket.get_terminate_reason()
        assert "30" in result
        flow.delete()

    def test_get_terminate_reason_user_terminated(self, base_ticket):
        """测试获取终止原因 - 用户终止"""
        base_ticket.status = TicketStatus.TERMINATED
        base_ticket.updater = "dba_user"
        base_ticket.save()

        flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.TERMINATED,
            err_code=FlowErrCode.GENERAL_ERROR,
            context={"remark": "手动终止测试"},
            details={},
        )

        result = base_ticket.get_terminate_reason()
        assert "dba_user" in result
        assert "手动终止测试" in result
        flow.delete()

    def test_get_current_operators_with_todo(self, base_ticket):
        """测试获取当前处理人 - 有待办时返回处理人和协助人"""
        flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.RUNNING,
            details={},
        )
        todo = Todo.objects.create(
            ticket=base_ticket,
            flow=flow,
            name="人工确认",
            type=TodoType.INNER_APPROVE,
            status=TodoStatus.TODO,
            operators=["admin", "dba1"],
        )

        result = base_ticket.get_current_operators()
        assert result["operators"] == ["admin", "dba1"]
        todo.delete()
        flow.delete()

    def test_get_current_operators_no_todo(self, base_ticket):
        """测试获取当前处理人 - 无待办时返回空列表"""
        result = base_ticket.get_current_operators()
        assert result["operators"] == []
        assert result["helpers"] == []

    def test_update_details(self, base_ticket):
        """测试更新单据详情"""
        base_ticket.update_details(extra_key="extra_value")

        base_ticket.refresh_from_db()
        assert base_ticket.details["extra_key"] == "extra_value"
        assert base_ticket.details["nodes"] == {"backend": []}

    def test_update_flow_details(self, base_ticket):
        """测试代理更新流程详情"""
        flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.RUNNING,
            details={},
        )

        base_ticket.update_flow_details(task_id="proxy_test", extra="data")

        flow.refresh_from_db()
        assert flow.details["task_id"] == "proxy_test"
        assert flow.details["extra"] == "data"
        flow.delete()

    def test_current_flow_with_running_flow(self, running_ticket, running_flow):
        """测试获取当前流程 - 有非 PENDING 流程时返回最后一个"""
        result = running_ticket.current_flow()
        assert result.id == running_flow.id

    def test_current_flow_all_pending(self, base_ticket, base_flow):
        """测试获取当前流程 - 所有流程都是 PENDING 时返回第一个"""
        result = base_ticket.current_flow()
        assert result.id == base_flow.id

    def test_next_flow(self, base_ticket, base_flow):
        """测试获取下一个流程"""
        result = base_ticket.next_flow()
        assert result.id == base_flow.id

    def test_next_flow_with_itsm_skip(self, base_ticket):
        """测试获取下一个流程 - ITSM_FLOW_SKIP 启用时跳过审批和暂停流程"""
        itsm_flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.BK_ITSM,
            status=TicketFlowStatus.PENDING,
            details={},
        )
        inner_flow = Flow.objects.create(
            ticket=base_ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.PENDING,
            details={},
        )

        with patch("backend.ticket.models.ticket.env") as mock_env:
            mock_env.ITSM_FLOW_SKIP = True
            result = base_ticket.next_flow()

        assert result.id == inner_flow.id
        itsm_flow.delete()
        inner_flow.delete()

    def test_add_related_ticket_with_ticket_object(self, base_ticket):
        """测试关联单据 - 传入 Ticket 对象"""
        related_ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_HA_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="关联单据",
            details={},
            group=DBType.MySQL.value,
        )

        base_ticket.add_related_ticket(related_ticket, done=True)

        delivery_flow = Flow.objects.filter(ticket=base_ticket, flow_type=FlowType.DELIVERY).first()
        assert delivery_flow is not None
        assert delivery_flow.details["related_ticket"] == related_ticket.id
        assert delivery_flow.status == TicketFlowStatus.SUCCEEDED
        delivery_flow.delete()
        related_ticket.delete()

    def test_add_related_ticket_with_id(self, base_ticket):
        """测试关联单据 - 传入单据 ID"""
        related_ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_HA_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="关联单据",
            details={},
            group=DBType.MySQL.value,
        )

        base_ticket.add_related_ticket(related_ticket.id, done=False)

        delivery_flow = Flow.objects.filter(ticket=base_ticket, flow_type=FlowType.DELIVERY).first()
        assert delivery_flow is not None
        assert delivery_flow.status == TicketFlowStatus.PENDING
        delivery_flow.delete()
        related_ticket.delete()

    def test_add_related_ticket_invalid_type(self, base_ticket):
        """测试关联单据 - 传入无效类型抛出 TypeError"""
        with pytest.raises(TypeError):
            base_ticket.add_related_ticket(12.5)

    def test_create_ticket_basic(self):
        """测试 create_ticket - 基础创建流程"""
        mock_builder_cls = MagicMock()
        mock_builder_cls.group = DBType.MySQL.value
        mock_builder = MagicMock()

        with patch("backend.ticket.builders.BuilderFactory") as mock_factory, patch(
            "backend.ticket.models.ticket.observe"
        ) as mock_observe, patch("backend.ticket.flow_manager.manager.TicketFlowManager") as mock_fm:
            mock_observe.return_value.__enter__ = MagicMock(return_value=None)
            mock_observe.return_value.__exit__ = MagicMock(return_value=False)
            mock_factory.get_builder_cls.return_value = mock_builder_cls
            mock_factory.create_builder.return_value = mock_builder

            ticket = Ticket.create_ticket(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                creator="admin",
                bk_biz_id=constant.BK_BIZ_ID,
                remark="测试自动创建",
                details={"nodes": {}},
                auto_execute=True,
            )

        assert Ticket.objects.filter(id=ticket.id).exists()
        assert ticket.ticket_type == TicketType.MYSQL_SINGLE_APPLY
        assert ticket.bk_biz_id == constant.BK_BIZ_ID
        mock_builder.patch_ticket_detail.assert_called_once()
        mock_builder.init_ticket_flows.assert_called_once()
        mock_fm.assert_called_once()
        ticket.delete()

    def test_create_ticket_no_auto_execute(self):
        """测试 create_ticket - auto_execute=False 不启动流程"""
        mock_builder_cls = MagicMock()
        mock_builder_cls.group = DBType.MySQL.value
        mock_builder = MagicMock()

        with patch("backend.ticket.builders.BuilderFactory") as mock_factory, patch(
            "backend.ticket.models.ticket.observe"
        ) as mock_observe:
            mock_observe.return_value.__enter__ = MagicMock(return_value=None)
            mock_observe.return_value.__exit__ = MagicMock(return_value=False)
            mock_factory.get_builder_cls.return_value = mock_builder_cls
            mock_factory.create_builder.return_value = mock_builder

            ticket = Ticket.create_ticket(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                creator="admin",
                bk_biz_id=constant.BK_BIZ_ID,
                remark="测试不自动执行",
                details={"nodes": {}},
                auto_execute=False,
            )

        assert Ticket.objects.filter(id=ticket.id).exists()
        ticket.delete()

    def test_create_ticket_with_helpers_and_msg_config(self):
        """测试 create_ticket - 带协助人和消息配置"""
        mock_builder_cls = MagicMock()
        mock_builder_cls.group = DBType.MySQL.value
        mock_builder = MagicMock()

        with patch("backend.ticket.builders.BuilderFactory") as mock_factory, patch(
            "backend.ticket.models.ticket.observe"
        ) as mock_observe, patch("backend.ticket.flow_manager.manager.TicketFlowManager"):
            mock_observe.return_value.__enter__ = MagicMock(return_value=None)
            mock_observe.return_value.__exit__ = MagicMock(return_value=False)
            mock_factory.get_builder_cls.return_value = mock_builder_cls
            mock_factory.create_builder.return_value = mock_builder

            ticket = Ticket.create_ticket(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                creator="admin",
                bk_biz_id=constant.BK_BIZ_ID,
                remark="带配置创建",
                details={"nodes": {}},
                send_msg_config={"type": "email"},
                helpers=["dba1", "dba2"],
            )

        assert ticket.config["send_msg_config"] == {"type": "email"}
        assert ticket.config["helpers"] == ["dba1", "dba2"]
        ticket.delete()

    def test_create_ticket_from_bk_monitor(self):
        """测试 create_ticket_from_bk_monitor - 从蓝鲸监控创建单据"""
        mock_serializer = MagicMock()
        mock_serializer.return_value.to_internal_value.return_value = {"nodes": {}}
        mock_builder_cls = MagicMock()
        mock_builder_cls.alarm_transform_serializer = mock_serializer

        callback_data = {
            "ticket_types": [TicketType.MYSQL_SINGLE_APPLY],
            "creator": "admin",
            "callback_message": {
                "event": {
                    "dimensions": {"appid": constant.BK_BIZ_ID},
                    "id": "event_001",
                }
            },
        }

        with patch("backend.ticket.builders.BuilderFactory") as mock_factory, patch.object(
            Ticket, "create_ticket"
        ) as mock_create:
            mock_factory.get_builder_cls.return_value = mock_builder_cls
            Ticket.create_ticket_from_bk_monitor(callback_data)

        mock_create.assert_called_once()

    def test_create_ticket_from_bk_monitor_no_serializer(self):
        """测试 create_ticket_from_bk_monitor - 无 alarm_transform_serializer 抛出异常"""
        mock_builder_cls = MagicMock()
        mock_builder_cls.alarm_transform_serializer = None

        callback_data = {
            "ticket_types": [TicketType.MYSQL_SINGLE_APPLY],
            "creator": "admin",
            "callback_message": {
                "event": {
                    "dimensions": {"appid": constant.BK_BIZ_ID},
                    "id": "event_002",
                }
            },
        }

        with patch("backend.ticket.builders.BuilderFactory") as mock_factory:
            mock_factory.get_builder_cls.return_value = mock_builder_cls
            with pytest.raises(Exception):
                Ticket.create_ticket_from_bk_monitor(callback_data)


# ==================== TestTicketFlowsConfig ====================


class TestTicketFlowsConfig:
    """测试 TicketFlowsConfig 模型"""

    def test_create_and_query(self, ticket_flows_config):
        """测试创建和查询"""
        assert TicketFlowsConfig.objects.filter(id=ticket_flows_config.id).exists()
        saved = TicketFlowsConfig.objects.get(id=ticket_flows_config.id)
        assert saved.bk_biz_id == PLAT_BIZ_ID
        assert saved.ticket_type == TicketType.MYSQL_SINGLE_APPLY

    def test_get_config(self, ticket_flows_config):
        """测试获取平台配置"""
        result = TicketFlowsConfig.get_config(TicketType.MYSQL_SINGLE_APPLY)
        assert result.id == ticket_flows_config.id
        assert result.configs == {"need_itsm": False, "need_manual_confirm": False}

    def test_get_cluster_configs_no_cluster_ids(self, ticket_flows_config):
        """测试获取集群配置 - 不涉及集群时返回业务/平台配置"""
        result = TicketFlowsConfig.get_cluster_configs(
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_ids=[],
        )
        assert len(result) == 1
        assert result[0].id == ticket_flows_config.id

    def test_get_cluster_configs_with_biz_config(self, ticket_flows_config):
        """测试获取集群配置 - 有业务配置时优先使用业务配置"""
        biz_config = TicketFlowsConfig.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            group=DBType.MySQL.value,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            editable=True,
            configs={"need_itsm": True, "need_manual_confirm": True},
            creator="admin",
            updater="admin",
        )

        result = TicketFlowsConfig.get_cluster_configs(
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_ids=[],
        )
        assert len(result) == 1
        assert result[0].configs["need_itsm"] is True
        biz_config.delete()

    def test_get_cluster_configs_with_cluster_config(self, ticket_flows_config):
        """测试获取集群配置 - 有集群配置时优先使用集群配置"""
        cluster_config = TicketFlowsConfig.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_ids=[
                {"id": 5001, "immute_domain": "mysql-test-1.example.com"},
                {"id": 5002, "immute_domain": "mysql-test-2.example.com"},
            ],
            group=DBType.MySQL.value,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            editable=True,
            configs={"need_itsm": True, "need_manual_confirm": False},
            creator="admin",
            updater="admin",
        )

        result = TicketFlowsConfig.get_cluster_configs(
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_ids=[5001],
        )
        assert len(result) == 1
        assert result[0].configs["need_itsm"] is True
        cluster_config.delete()


# ==================== TestClusterOperateRecordManager ====================


class TestClusterOperateRecordManager:
    """测试 ClusterOperateRecordManager"""

    def test_filter_actives(self, cluster_operate_record, running_ticket):
        """测试过滤活跃记录"""
        result = ClusterOperateRecord.objects.filter_actives(cluster_id=3001)
        assert result.count() == 1
        assert result.first().id == cluster_operate_record.id

    def test_filter_actives_no_match(self, cluster_operate_record):
        """测试过滤活跃记录 - 无匹配"""
        result = ClusterOperateRecord.objects.filter_actives(cluster_id=9999)
        assert result.count() == 0

    def test_filter_inner_actives(self, cluster_operate_record, running_ticket, running_flow):
        """测试过滤 inner flow 活跃记录"""
        result = ClusterOperateRecord.objects.filter_inner_actives(cluster_id=3001)
        assert result.count() == 1

    def test_filter_inner_actives_exclude_ticket(self, cluster_operate_record, running_ticket, running_flow):
        """测试过滤 inner flow 活跃记录 - 排除指定单据"""
        result = ClusterOperateRecord.objects.filter_inner_actives(
            cluster_id=3001, exclude_ticket_ids=[running_ticket.id]
        )
        assert result.count() == 0

    def test_filter_inner_actives_with_lock(self, cluster_operate_record, running_ticket, running_flow):
        """测试过滤 inner flow 活跃记录（带锁）"""
        result = ClusterOperateRecord.objects.filter_inner_actives_with_lock(cluster_id=3001)
        assert result.count() == 1
        assert result.first().id == cluster_operate_record.id

    def test_get_cluster_active_operations(self, cluster_operate_record, running_ticket, running_flow):
        """测试获取集群活跃操作列表"""
        result = ClusterOperateRecord.objects.get_cluster_active_operations(cluster_id=3001)
        assert len(result) == 1
        assert result[0]["ticket_id"] == running_ticket.id
        assert result[0]["cluster_id"] == 3001

    def test_has_exclusive_operations_with_lock_mutual_exclusive(
        self, cluster_operate_record, running_ticket, running_flow
    ):
        """测试互斥判断（带锁） - 存在互斥单据"""
        mock_map = {TicketType.MYSQL_SINGLE_APPLY: {TicketType.MYSQL_HA_APPLY: True}}
        with patch.object(
            ClusterOperateRecord.objects,
            "get_exclusive_ticket_map",
            return_value=mock_map,
        ):
            result = ClusterOperateRecord.objects.has_exclusive_operations_with_lock(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                cluster_id=3001,
            )

        assert len(result) == 1
        assert result[0]["exclusive_ticket"].id == running_ticket.id

    def test_has_exclusive_operations_with_lock_no_exclusive(
        self, cluster_operate_record, running_ticket, running_flow
    ):
        """测试互斥判断（带锁） - 不互斥"""
        mock_map = {TicketType.MYSQL_SINGLE_APPLY: {TicketType.MYSQL_HA_APPLY: False}}
        with patch.object(
            ClusterOperateRecord.objects,
            "get_exclusive_ticket_map",
            return_value=mock_map,
        ):
            result = ClusterOperateRecord.objects.has_exclusive_operations_with_lock(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                cluster_id=3001,
            )

        assert len(result) == 0

    def test_has_exclusive_operations_with_lock_unlock_wildcard(
        self, cluster_operate_record, running_ticket, running_flow
    ):
        """测试互斥判断（带锁） - 通配符解锁"""
        cluster_operate_record.unlock_ticket_type_condition = ["*"]
        cluster_operate_record.save()

        mock_map = {TicketType.MYSQL_SINGLE_APPLY: {TicketType.MYSQL_HA_APPLY: True}}
        with patch.object(
            ClusterOperateRecord.objects,
            "get_exclusive_ticket_map",
            return_value=mock_map,
        ):
            result = ClusterOperateRecord.objects.has_exclusive_operations_with_lock(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                cluster_id=3001,
            )

        assert len(result) == 0

    def test_has_exclusive_operations_with_lock_unlock_specific_type(
        self, cluster_operate_record, running_ticket, running_flow
    ):
        """测试互斥判断（带锁） - 指定类型解锁"""
        cluster_operate_record.unlock_ticket_type_condition = [TicketType.MYSQL_SINGLE_APPLY]
        cluster_operate_record.save()

        mock_map = {TicketType.MYSQL_SINGLE_APPLY: {TicketType.MYSQL_HA_APPLY: True}}
        with patch.object(
            ClusterOperateRecord.objects,
            "get_exclusive_ticket_map",
            return_value=mock_map,
        ):
            result = ClusterOperateRecord.objects.has_exclusive_operations_with_lock(
                ticket_type=TicketType.MYSQL_SINGLE_APPLY,
                cluster_id=3001,
            )

        assert len(result) == 0

    def test_get_exclusive_ticket_map_from_excel(self):
        """测试获取互斥矩阵 - 从 Excel 解析"""
        result = ClusterOperateRecord.objects.get_exclusive_ticket_map()
        assert isinstance(result, dict)


# ==================== TestClusterOperateRecord ====================


class TestClusterOperateRecord:
    """测试 ClusterOperateRecord 模型"""

    def test_create_and_query(self, cluster_operate_record):
        """测试创建和查询"""
        assert ClusterOperateRecord.objects.filter(id=cluster_operate_record.id).exists()
        saved = ClusterOperateRecord.objects.get(id=cluster_operate_record.id)
        assert saved.cluster_id == 3001

    def test_summary_property(self, cluster_operate_record, running_ticket):
        """测试 summary 属性"""
        result = cluster_operate_record.summary
        assert result["operator"] == "admin"
        assert result["cluster_id"] == 3001
        assert result["ticket_id"] == running_ticket.id
        assert result["ticket_type"] == running_ticket.ticket_type
        assert result["status"] == running_ticket.status

    def test_get_cluster_records_map(self, cluster_operate_record, running_ticket):
        """测试获取集群操作记录映射"""
        result = ClusterOperateRecord.get_cluster_records_map([3001])
        assert 3001 in result
        assert len(result[3001]) == 1
        assert result[3001][0]["ticket_id"] == running_ticket.id

    def test_get_cluster_records_map_empty(self):
        """测试获取集群操作记录映射 - 无记录"""
        result = ClusterOperateRecord.get_cluster_records_map([9999])
        assert 9999 not in result

    def test_unlock_ticket_type_operations_default(self, cluster_operate_record):
        """测试解锁单据类型 - 默认全解锁"""
        cluster_operate_record.unlock_ticket_type_operations()

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.unlock_ticket_type_condition == ["*"]

    def test_unlock_ticket_type_operations_specific(self, cluster_operate_record):
        """测试解锁单据类型 - 指定类型"""
        cluster_operate_record.unlock_ticket_type_operations(
            [TicketType.MYSQL_SINGLE_APPLY, TicketType.MYSQL_HA_APPLY]
        )

        cluster_operate_record.refresh_from_db()
        assert set(cluster_operate_record.unlock_ticket_type_condition) == {
            TicketType.MYSQL_SINGLE_APPLY,
            TicketType.MYSQL_HA_APPLY,
        }

    def test_unlock_ticket_type_operations_wildcard_in_list(self, cluster_operate_record):
        """测试解锁单据类型 - 列表中包含通配符"""
        cluster_operate_record.unlock_ticket_type_operations(["*", TicketType.MYSQL_SINGLE_APPLY])

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.unlock_ticket_type_condition == ["*"]

    def test_unlock_ticket_type_operations_invalid_type(self, cluster_operate_record):
        """测试解锁单据类型 - 传入非列表类型抛出 TypeError"""
        with pytest.raises(TypeError):
            cluster_operate_record.unlock_ticket_type_operations("invalid")

    def test_unlock_ticket_type_operations_merge(self, cluster_operate_record):
        """测试解锁单据类型 - 合并去重"""
        cluster_operate_record.unlock_ticket_type_condition = [TicketType.MYSQL_SINGLE_APPLY]
        cluster_operate_record.save()

        cluster_operate_record.unlock_ticket_type_operations(
            [TicketType.MYSQL_SINGLE_APPLY, TicketType.MYSQL_HA_APPLY]
        )

        cluster_operate_record.refresh_from_db()
        assert set(cluster_operate_record.unlock_ticket_type_condition) == {
            TicketType.MYSQL_SINGLE_APPLY,
            TicketType.MYSQL_HA_APPLY,
        }

    def test_remove_unlock_ticket_type_config_operations_default(self, cluster_operate_record):
        """测试移除解锁配置 - 默认不移除"""
        cluster_operate_record.unlock_ticket_type_condition = [TicketType.MYSQL_SINGLE_APPLY]
        cluster_operate_record.save()

        cluster_operate_record.remove_unlock_ticket_type_config_operations()

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.unlock_ticket_type_condition == [TicketType.MYSQL_SINGLE_APPLY]

    def test_remove_unlock_ticket_type_config_operations_specific(self, cluster_operate_record):
        """测试移除解锁配置 - 移除指定类型"""
        cluster_operate_record.unlock_ticket_type_condition = [
            TicketType.MYSQL_SINGLE_APPLY,
            TicketType.MYSQL_HA_APPLY,
        ]
        cluster_operate_record.save()

        cluster_operate_record.remove_unlock_ticket_type_config_operations([TicketType.MYSQL_SINGLE_APPLY])

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.unlock_ticket_type_condition == [TicketType.MYSQL_HA_APPLY]

    def test_remove_unlock_ticket_type_config_operations_wildcard(self, cluster_operate_record):
        """测试移除解锁配置 - 通配符全部移除"""
        cluster_operate_record.unlock_ticket_type_condition = [
            TicketType.MYSQL_SINGLE_APPLY,
            TicketType.MYSQL_HA_APPLY,
        ]
        cluster_operate_record.save()

        cluster_operate_record.remove_unlock_ticket_type_config_operations(["*"])

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.unlock_ticket_type_condition == []

    def test_remove_unlock_ticket_type_config_operations_invalid_type(self, cluster_operate_record):
        """测试移除解锁配置 - 传入非列表类型抛出 TypeError"""
        with pytest.raises(TypeError):
            cluster_operate_record.remove_unlock_ticket_type_config_operations("invalid")

    def test_has_exclusive_operations_pause_no_exclusive(self, cluster_operate_record):
        """测试暂停互斥判断 - 无互斥单据时可运行"""
        cluster_operate_record.is_pause = True
        cluster_operate_record.save()

        with patch.object(
            ClusterOperateRecord.objects,
            "has_exclusive_operations_with_lock",
            return_value=[],
        ):
            can_run, infos = cluster_operate_record.has_exclusive_operations_pause()

        assert can_run is True
        assert infos == []
        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.is_pause is False

    def test_has_exclusive_operations_pause_with_exclusive(self, cluster_operate_record):
        """测试暂停互斥判断 - 存在互斥单据时不可运行"""
        exclusive_info = [{"exclusive_ticket": MagicMock(), "root_id": "fake_root"}]
        with patch.object(
            ClusterOperateRecord.objects,
            "has_exclusive_operations_with_lock",
            return_value=exclusive_info,
        ):
            can_run, infos = cluster_operate_record.has_exclusive_operations_pause()

        assert can_run is False
        assert len(infos) == 1

    def test_update_is_pause_with_pause(self, cluster_operate_record):
        """测试更新暂停状态"""
        cluster_operate_record.is_pause = False
        cluster_operate_record.save()

        cluster_operate_record.update_is_pause_with_pause()

        cluster_operate_record.refresh_from_db()
        assert cluster_operate_record.is_pause is True


# ==================== TestInstanceOperateRecordManager ====================


class TestInstanceOperateRecordManager:
    """测试 InstanceOperateRecordManager"""

    def test_filter_actives(self, instance_operate_record, running_ticket):
        """测试过滤活跃记录"""
        result = InstanceOperateRecord.objects.filter_actives(instance_id=f"{cc.NORMAL_IP}:3306")
        assert result.count() == 1
        assert result.first().id == instance_operate_record.id

    def test_filter_actives_no_match(self, instance_operate_record):
        """测试过滤活跃记录 - 无匹配"""
        result = InstanceOperateRecord.objects.filter_actives(instance_id=f"{cc.NORMAL_IP2}:3306")
        assert result.count() == 0

    def test_get_locking_operations(self, instance_operate_record, running_ticket):
        """测试获取锁定操作列表"""
        result = InstanceOperateRecord.objects.get_locking_operations(instance_id=f"{cc.NORMAL_IP}:3306")
        assert len(result) == 1
        assert result[0]["instance_id"] == f"{cc.NORMAL_IP}:3306"
        assert result[0]["ticket_id"] == running_ticket.id

    def test_has_locked_operations_true(self, instance_operate_record, running_ticket):
        """测试是否有锁定操作 - 有"""
        result = InstanceOperateRecord.objects.has_locked_operations(instance_id=f"{cc.NORMAL_IP}:3306")
        assert result is True

    def test_has_locked_operations_false(self, instance_operate_record):
        """测试是否有锁定操作 - 无"""
        result = InstanceOperateRecord.objects.has_locked_operations(instance_id=f"{cc.NORMAL_IP2}:3306")
        assert result is False


# ==================== TestInstanceOperateRecord ====================


class TestInstanceOperateRecord:
    """测试 InstanceOperateRecord 模型"""

    def test_create_and_query(self, instance_operate_record):
        """测试创建和查询"""
        assert InstanceOperateRecord.objects.filter(id=instance_operate_record.id).exists()
        saved = InstanceOperateRecord.objects.get(id=instance_operate_record.id)
        assert saved.instance_id == f"{cc.NORMAL_IP}:3306"

    def test_summary_property(self, instance_operate_record, running_ticket):
        """测试 summary 属性"""
        result = instance_operate_record.summary
        assert result["operator"] == "admin"
        assert result["instance_id"] == f"{cc.NORMAL_IP}:3306"
        assert result["ticket_id"] == running_ticket.id
        assert result["ticket_type"] == running_ticket.ticket_type
        assert result["status"] == running_ticket.status

    def test_get_instance_records_map(self, instance_operate_record, running_ticket):
        """测试获取实例操作记录映射"""
        result = InstanceOperateRecord.get_instance_records_map([f"{cc.NORMAL_IP}:3306"])
        assert f"{cc.NORMAL_IP}:3306" in result
        assert len(result[f"{cc.NORMAL_IP}:3306"]) == 1
        assert result[f"{cc.NORMAL_IP}:3306"][0]["ticket_id"] == running_ticket.id

    def test_get_instance_records_map_empty(self):
        """测试获取实例操作记录映射 - 无记录"""
        result = InstanceOperateRecord.get_instance_records_map([f"{cc.NORMAL_IP2}:9999"])
        assert f"{cc.NORMAL_IP2}:9999" not in result


# ==================== TransactionTestCase — 唯一约束测试 ====================
# ⚠️ TransactionTestCase 必须放在文件末尾（DS4）
# ⚠️ setUp 必须自包含，tearDown 必须完整清理
# ⚠️ TransactionTestCase 会在每个测试方法后 flush 所有表数据


class TestClusterOperateRecordUniqueConstraint(TransactionTestCase):
    """测试 ClusterOperateRecord 唯一约束

    注意：TransactionTestCase 会在每个测试方法执行后 flush 所有数据库表。
    因此 setUp 必须自包含创建所有依赖数据，tearDown 必须完整清理。
    """

    def setUp(self):
        """创建测试数据"""
        self.ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_HA_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="唯一约束测试单据",
            details={},
            group=DBType.MySQL.value,
        )
        self.flow = Flow.objects.create(
            ticket=self.ticket,
            flow_type=FlowType.INNER_FLOW,
            status=TicketFlowStatus.RUNNING,
            details={},
        )
        self.record = ClusterOperateRecord.objects.create(
            cluster_id=4001,
            flow=self.flow,
            ticket=self.ticket,
            creator="admin",
            updater="admin",
        )

    def test_unique_together_constraint(self):
        """测试 cluster_id + flow + ticket 唯一约束"""
        with self.assertRaises(Exception):
            ClusterOperateRecord.objects.create(
                cluster_id=4001,
                flow=self.flow,
                ticket=self.ticket,
                creator="admin",
                updater="admin",
            )

    def test_different_cluster_id_allowed(self):
        """测试不同 cluster_id 允许创建"""
        record2 = ClusterOperateRecord.objects.create(
            cluster_id=4002,
            flow=self.flow,
            ticket=self.ticket,
            creator="admin",
            updater="admin",
        )
        self.assertEqual(ClusterOperateRecord.objects.filter(ticket=self.ticket).count(), 2)
        record2.delete()

    def tearDown(self):
        """清理测试数据"""
        ClusterOperateRecord.objects.filter(ticket=self.ticket).delete()
        Flow.objects.filter(ticket=self.ticket).delete()
        self.ticket.delete()
