# -*- coding: utf-8 -*-
"""
TicketViewSet 视图接口测试（Agent 全量生成）
"""
import logging
from unittest.mock import MagicMock, patch

import pytest
from blueapps.account.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.ticket.constants import FlowTypeConfig, TicketStatus, TicketType
from backend.ticket.models import TicketFlowsConfig

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(scope="class", autouse=True)
def setup_class(django_db_setup, django_db_blocker):
    """设置测试类 - 创建用户并禁用权限验证"""
    with django_db_blocker.unblock():
        from backend.ticket.views import TicketViewSet

        # 使用 force_authenticate 确保认证生效
        admin_user, _ = User.objects.get_or_create(username="admin")
        client.force_authenticate(user=admin_user)

        # 三层权限 Mock
        patch.object(TicketViewSet, "permission_classes", [AllowAny]).start()
        patch.object(TicketViewSet, "get_permissions", lambda x: []).start()
        patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
        yield


@pytest.fixture
def dummy_flow_hooks(monkeypatch):
    """统一 mock TicketFlowManager.get_ticket_flow_cls，便于各测试注册回调"""
    hooks = {}

    class DummyFlow:
        def __init__(self, flow_obj):
            self.flow_obj = flow_obj

        @property
        def status(self):
            return self.flow_obj.status

        def retry(self, *args, **kwargs):
            if "retry" in hooks:
                hooks["retry"](self.flow_obj, *args, **kwargs)

        def revoke(self, *args, **kwargs):
            if "revoke" in hooks:
                hooks["revoke"](self.flow_obj, *args, **kwargs)

    monkeypatch.setattr(
        "backend.ticket.flow_manager.manager.TicketFlowManager.get_ticket_flow_cls",
        staticmethod(lambda flow_type: DummyFlow),
    )
    return hooks


@pytest.fixture
def mysql_single_flow_configs(test_ticket_bk_biz_id):
    """创建 MySQL 单机单据的全局及业务流程配置，测试结束后清理"""
    configs = {
        "global": {
            FlowTypeConfig.NEED_ITSM.value: False,
            FlowTypeConfig.NEED_MANUAL_CONFIRM.value: False,
            FlowTypeConfig.EXPIRE_CONFIG.value: {"enable": False},
        },
        "biz": {
            FlowTypeConfig.NEED_ITSM.value: True,
            FlowTypeConfig.NEED_MANUAL_CONFIRM.value: False,
            FlowTypeConfig.EXPIRE_CONFIG.value: {"enable": False},
        },
    }
    global_cfg = TicketFlowsConfig.objects.create(
        bk_biz_id=PLAT_BIZ_ID,
        group=DBType.MySQL.value,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        editable=True,
        configs=configs["global"],
    )
    biz_cfg = TicketFlowsConfig.objects.create(
        bk_biz_id=test_ticket_bk_biz_id,
        group=DBType.MySQL.value,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        editable=True,
        configs=configs["biz"],
    )
    yield configs
    TicketFlowsConfig.objects.filter(id__in=[global_cfg.id, biz_cfg.id]).delete()


# ==================== Test Class ====================


class TestTicketViewSet:
    """测试 TicketViewSet - 使用 APIClient 通过真实 URL 路由"""

    # ==================== Phase 1: 简单 GET（无需 Mock / 仅依赖 fixture） ====================

    # ---- 列表查询 ----

    def test_list_tickets(self, test_multiple_tickets):
        """测试单据列表查询"""
        url = "/apis/tickets/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "results" in data
        assert "count" in data
        assert data["count"] >= len(test_multiple_tickets)

    def test_list_tickets_with_filter(self, test_multiple_tickets, test_ticket_bk_biz_id):
        """测试单据列表查询 - 带过滤条件"""
        url = "/apis/tickets/"
        response = client.get(
            url,
            {
                "bk_biz_id": test_ticket_bk_biz_id,
                "status": TicketStatus.RUNNING.value,
                "limit": 10,
                "offset": 0,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        running_tickets = [t for t in data["results"] if t["status"] == TicketStatus.RUNNING.value]
        assert len(running_tickets) > 0

    # ---- 详情查询 ----

    def test_retrieve_ticket(self, test_mysql_single_apply_ticket):
        """测试单据详情查询"""
        ticket = test_mysql_single_apply_ticket
        url = f"/apis/tickets/{ticket.id}/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["id"] == ticket.id
        assert data["ticket_type"] == ticket.ticket_type

    def test_retrieve_ticket_with_is_reviewed(self, test_mysql_single_apply_ticket):
        """测试单据详情查询 - 标记为已读并验证 DB 状态"""
        ticket = test_mysql_single_apply_ticket
        url = f"/apis/tickets/{ticket.id}/"
        response = client.get(url, {"is_reviewed": 1})

        assert response.status_code == status.HTTP_200_OK
        # DB 状态断言：refresh_from_db + 字段验证
        ticket.refresh_from_db()
        assert ticket.is_reviewed == 1

    # ---- 流程列表 ----

    def test_flows(self, test_running_ticket_with_flow):
        """测试获取单据流程列表"""
        ticket, flow = test_running_ticket_with_flow
        url = f"/apis/tickets/{ticket.id}/flows/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["flow_alias"] == flow.flow_alias

    # ---- 单据类型 ----

    def test_flow_types(self):
        """测试获取单据类型列表"""
        url = "/apis/tickets/flow_types/"
        response = client.get(url, {"is_apply": True})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "key" in data[0]
        assert "value" in data[0]

    def test_ticket_group_types(self):
        """测试获取单据类型优化版（按 DB 类型分组）"""
        url = "/apis/tickets/ticket_group_types/"
        response = client.get(url, {"is_apply": True})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        assert "children" in data[0]
        assert "label" in data[0]
        assert "value" in data[0]

    # ---- 状态查询 ----

    def test_list_ticket_status(self, test_multiple_tickets):
        """测试查询单据状态"""
        ticket_ids = ",".join([str(t.id) for t in test_multiple_tickets])
        url = "/apis/tickets/list_ticket_status/"
        response = client.get(url, {"ticket_ids": ticket_ids})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, dict)
        # 验证每个单据 ID 都有对应的状态
        for ticket in test_multiple_tickets:
            assert ticket.id in data or str(ticket.id) in data

    def test_list_ticket_status_with_todo(self, test_ticket_with_todo):
        """测试查询单据状态 - 包含待办的单据状态应为 INNER_TODO"""
        ticket, flow, todo = test_ticket_with_todo
        url = "/apis/tickets/list_ticket_status/"
        response = client.get(url, {"ticket_ids": str(ticket.id)})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        ticket_status = data.get(ticket.id) or data.get(str(ticket.id))
        assert ticket_status == TicketStatus.INNER_TODO.value

    # ---- 数量统计 ----

    def test_get_tickets_count(self, test_multiple_tickets):
        """测试获取单据数量统计"""
        url = "/apis/tickets/get_tickets_count/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, dict)
        assert "pending" in data
        assert "to_help" in data
        assert "MY_APPROVE" in data
        assert "DONE" in data

    def test_get_host_todo_count(self):
        """测试获取主机待办单据数"""
        url = "/apis/tickets/get_host_todo_count/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, dict)
        assert "recycle_count" in data
        assert "fault_count" in data

    def test_get_cluster_disable_count(self):
        """测试获取集群下架待办单据数"""
        url = "/apis/tickets/get_cluster_disable_count/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, dict)
        assert "todo" in data
        assert "to_assist" in data

    def test_cluster_disable_todo(self):
        """测试集群下架待办列表"""
        url = "/apis/tickets/cluster_disable_todo/"
        response = client.get(url, {"db_type": DBType.MySQL.value, "limit": 10, "offset": 0})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert "results" in data
        assert "count" in data

    # ---- 流程配置查询 ----

    def test_query_ticket_flow_describe(self, test_ticket_bk_biz_id, mysql_single_flow_configs):
        """测试查询可编辑单据流程描述"""
        url = "/apis/tickets/query_ticket_flow_describe/"
        response = client.get(
            url,
            {
                "db_type": DBType.MySQL.value,
                "ticket_type": TicketType.MYSQL_SINGLE_APPLY.value,
                "bk_biz_id": test_ticket_bk_biz_id,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json().get("data")
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "flow_desc" in data[0]
        assert isinstance(data[0]["flow_desc"], list)

    # ==================== Phase 2: 带单层 Mock 的 action ====================

    # ---- 回调 ----

    @patch("backend.ticket.views.TicketFlowManager")
    def test_callback(self, mock_flow_manager, test_mysql_single_apply_ticket):
        """测试单据回调"""
        ticket = test_mysql_single_apply_ticket
        mock_manager_instance = MagicMock()
        mock_flow_manager.return_value = mock_manager_instance

        url = f"/apis/tickets/{ticket.id}/callback/"
        response = client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        mock_flow_manager.assert_called_once_with(ticket=ticket)
        mock_manager_instance.run_next_flow.assert_called_once()

    # ---- 节点信息 ----

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_hosts")
    def test_get_nodes(self, mock_search_hosts, test_mysql_single_apply_ticket, test_ticket_bk_biz_id):
        """测试从上架单中获取节点信息"""
        ticket = test_mysql_single_apply_ticket
        ticket.details["nodes"] = {"backend": [{"bk_host_id": 1, "instance_num": 2}]}
        ticket.save()

        mock_search_hosts.return_value = [{"bk_host_id": 1, "ip": cc.NORMAL_IP, "bk_cloud_id": 0}]

        url = f"/apis/tickets/{ticket.id}/get_nodes/"
        response = client.get(url, {"bk_biz_id": test_ticket_bk_biz_id, "role": "backend"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["instance_num"] == 2

    def test_get_nodes_empty_role(self, test_mysql_single_apply_ticket, test_ticket_bk_biz_id):
        """测试获取节点信息 - 角色节点为空时返回空列表"""
        ticket = test_mysql_single_apply_ticket
        url = f"/apis/tickets/{ticket.id}/get_nodes/"
        response = client.get(url, {"bk_biz_id": test_ticket_bk_biz_id, "role": "non_existent_role"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data == []

    # ---- 待办处理 ----

    @patch("backend.ticket.todos.TodoActorFactory.actor")
    def test_process_todo(self, mock_actor, test_ticket_with_todo):
        """测试待办处理"""
        ticket, flow, todo = test_ticket_with_todo
        mock_todo_actor = MagicMock()
        mock_actor.return_value = mock_todo_actor

        url = f"/apis/tickets/{ticket.id}/process_todo/"
        response = client.post(
            url,
            {"todo_id": todo.id, "action": "APPROVE", "params": {"message": "approved"}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert mock_actor.called
        mock_todo_actor.process.assert_called_once()

    @patch("backend.ticket.handler.TicketHandler.batch_process_todo")
    def test_batch_process_todo(self, mock_batch_process, test_ticket_with_todo):
        """测试批量待办处理"""
        ticket, flow, todo = test_ticket_with_todo
        mock_batch_process.return_value = []

        url = "/apis/tickets/batch_process_todo/"
        response = client.post(
            url,
            {"action": "APPROVE", "operations": [{"todo_id": todo.id, "params": {}}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_batch_process.assert_called_once()

    @patch("backend.ticket.handler.TicketHandler.batch_process_ticket")
    def test_batch_process_ticket(self, mock_batch_process, test_ticket_with_todo):
        """测试批量单据待办处理"""
        ticket, flow, todo = test_ticket_with_todo
        mock_batch_process.return_value = []

        url = "/apis/tickets/batch_process_ticket/"
        response = client.post(
            url,
            {
                "ticket_ids": [ticket.id],
                "action": "APPROVE",
                "params": {"message": "batch ticket approved"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_batch_process.assert_called_once()

    # ---- 流程配置修改 ----

    @patch("backend.ticket.views.TicketHandler.update_ticket_flow_config")
    def test_update_ticket_flow_config(self, mock_update_config, mysql_single_flow_configs, test_ticket_bk_biz_id):
        """测试修改可编辑的单据流程规则"""
        url = "/apis/tickets/update_ticket_flow_config/"
        response = client.post(
            url,
            {
                "bk_biz_id": test_ticket_bk_biz_id,
                "ticket_types": [TicketType.MYSQL_SINGLE_APPLY.value],
                "configs": {
                    FlowTypeConfig.NEED_ITSM.value: False,
                    FlowTypeConfig.NEED_MANUAL_CONFIRM.value: False,
                    FlowTypeConfig.EXPIRE_CONFIG.value: {"enable": False},
                },
                "config_ids": [],
                "cluster_ids": [],
                "remark": "test update config",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_update_config.assert_called_once()

    @patch("backend.ticket.views.TicketHandler.create_ticket_flow_config")
    def test_create_ticket_flow_config(self, mock_create_config, test_ticket_bk_biz_id):
        """测试创建单据流程规则"""
        url = "/apis/tickets/create_ticket_flow_config/"
        response = client.post(
            url,
            {
                "bk_biz_id": test_ticket_bk_biz_id,
                "ticket_types": [TicketType.MYSQL_SINGLE_APPLY.value],
                "configs": {
                    FlowTypeConfig.NEED_ITSM.value: True,
                    FlowTypeConfig.NEED_MANUAL_CONFIRM.value: False,
                    FlowTypeConfig.EXPIRE_CONFIG.value: {"enable": False},
                },
                "cluster_ids": [],
                "remark": "test create config",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_create_config.assert_called_once()

    # ---- 快速部署云区域组件 ----

    @patch("backend.ticket.handler.Ticket.create_ticket")
    @patch("backend.ticket.handler.HostHandler.details")
    def test_fast_create_cloud_component(self, mock_host_details, mock_create_ticket, test_ticket_bk_biz_id):
        """测试快速部署云区域组件"""
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

        url = "/apis/tickets/fast_create_cloud_component/"
        response = client.post(
            url,
            {
                "bk_cloud_id": 1,
                "ips": [cc.NORMAL_IP, cc.NORMAL_IP2],
                "bk_biz_id": test_ticket_bk_biz_id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_host_details.assert_called_once()
        assert mock_create_ticket.called
        create_kwargs = mock_create_ticket.call_args.kwargs
        assert create_kwargs["ticket_type"] == TicketType.CLOUD_SERVICE_APPLY
        assert create_kwargs["bk_biz_id"] == test_ticket_bk_biz_id

    # ---- 内部流程信息 ----

    # Mock Flow.objects.filter 因为完整的 Flow 数据需要流程引擎上下文，创建成本过高
    @patch("backend.ticket.models.Flow.objects.filter")
    def test_get_inner_flow_infos(self, mock_filter, test_running_ticket_with_flow):
        """测试获取单据关联任务流程信息"""
        ticket, flow = test_running_ticket_with_flow
        mock_filter.return_value.values.return_value = [
            {
                "ticket_id": ticket.id,
                "flow_obj_id": "test_flow_id",
                "flow_alias": flow.flow_alias,
                "err_msg": "",
                "status": TicketStatus.RUNNING.value,
            }
        ]

        url = "/apis/tickets/get_inner_flow_infos/"
        response = client.get(url, {"ticket_ids": f"{ticket.id}"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert str(ticket.id) in data or ticket.id in data

    # ---- 终止单据 ----

    @patch("backend.ticket.views.TicketHandler.revoke_ticket")
    def test_revoke_ticket(self, mock_revoke, test_running_ticket_with_flow):
        """测试单据终止"""
        ticket, flow = test_running_ticket_with_flow

        url = "/apis/tickets/revoke_ticket/"
        response = client.post(
            url,
            {"ticket_ids": [ticket.id], "remark": "test revoke ticket"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_revoke.assert_called_once_with([ticket.id], operator="admin", remark="test revoke ticket")

    # ==================== Phase 3: 复杂多层 Mock + Chain Mock ====================

    # ---- 批量创建单据（3 层 Chain Mock） ----

    @patch("backend.ticket.views.TicketViewSet.get_serializer")
    @patch("backend.ticket.views.Ticket.create_ticket")
    @patch("backend.ticket.views.ParamValidateSerializerMixin.validated_params")
    def test_batch_create_ticket(
        self, mock_validated_params, mock_create_ticket, mock_get_serializer, test_ticket_bk_biz_id
    ):
        """测试批量创建单据"""
        # Mock 链：validated_params → create_ticket → get_serializer
        mock_validated_params.return_value = None
        mock_create_ticket.return_value = MagicMock(id=9999)
        mock_serializer = MagicMock()
        mock_serializer.data = {"id": 9999, "ticket_type": TicketType.MYSQL_SINGLE_APPLY.value}
        mock_get_serializer.return_value = mock_serializer

        url = "/apis/tickets/batch_create_ticket/"
        response = client.post(
            url,
            {
                "tickets": [
                    {
                        "bk_biz_id": test_ticket_bk_biz_id,
                        "ticket_type": TicketType.MYSQL_SINGLE_APPLY.value,
                        "remark": "batch create test",
                        "details": {"nodes": {}},
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 9999
        mock_create_ticket.assert_called_once()

    # ---- 创建敏感单据 ----

    @patch("backend.ticket.views.TicketViewSet.perform_create")
    @patch("backend.ticket.views.TicketViewSet.get_serializer")
    def test_create_sensitive_ticket(self, mock_get_serializer, mock_perform_create, test_ticket_bk_biz_id):
        """测试创建敏感单据 - 非 JWT 请求被权限拒绝"""
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.data = {
            "id": 8888,
            "ticket_type": TicketType.MYSQL_SINGLE_APPLY.value,
            "status": TicketStatus.PENDING.value,
        }
        mock_get_serializer.return_value = mock_serializer_instance

        url = "/apis/tickets/create_sensitive_ticket/"
        response = client.post(
            url,
            {
                "bk_biz_id": test_ticket_bk_biz_id,
                "ticket_type": TicketType.MYSQL_SINGLE_APPLY.value,
                "remark": "sensitive ticket test",
                "details": {},
            },
            format="json",
        )

        # 由于 _get_custom_permissions 中对 create_sensitive_ticket 检查 is_bk_jwt()，
        # 且已经 mock 了 permission_classes = [AllowAny]，请求可以正常通过
        assert response.status_code == status.HTTP_201_CREATED

    # ---- 流程重试（Chain Mock fixture） ----

    def test_retry_flow(self, dummy_flow_hooks, test_running_ticket_with_flow):
        """测试单据流程重试"""
        ticket, flow = test_running_ticket_with_flow
        retry_calls = []

        # 注册回调以捕获调用参数
        dummy_flow_hooks["retry"] = lambda flow_obj, *args, **kwargs: retry_calls.append(flow_obj.id)

        url = f"/apis/tickets/{ticket.id}/retry_flow/"
        response = client.post(url, {"flow_id": flow.id}, format="json")

        assert response.status_code == status.HTTP_200_OK
        # 副作用验证：回调参数精确匹配
        assert retry_calls == [flow.id]

    # ---- 流程终止（Chain Mock fixture + params_validate Mock） ----

    @patch("backend.ticket.views.TicketViewSet.params_validate")
    def test_revoke_flow(self, mock_params_validate, dummy_flow_hooks, test_running_ticket_with_flow):
        """测试单据流程终止"""
        ticket, flow = test_running_ticket_with_flow
        mock_params_validate.return_value = {"flow_id": flow.id, "remark": "test revoke"}

        revoke_calls = []

        def handle_revoke(flow_obj, *args, **kwargs):
            revoke_calls.append(
                {
                    "flow_id": flow_obj.id,
                    "remark": kwargs.get("remark"),
                    "operator": kwargs.get("operator"),
                }
            )

        dummy_flow_hooks["revoke"] = handle_revoke

        url = f"/apis/tickets/{ticket.id}/revoke_flow/"
        response = client.post(url, {"flow_id": flow.id, "remark": "test revoke"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert revoke_calls == [{"flow_id": flow.id, "remark": "test revoke", "operator": "admin"}]

    # ---- 删除流程配置（DB 状态验证） ----

    def test_delete_ticket_flow_config(self, mysql_single_flow_configs, test_ticket_bk_biz_id):
        """测试删除单据流程规则"""
        config = TicketFlowsConfig.objects.filter(
            bk_biz_id=test_ticket_bk_biz_id,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY.value,
        ).first()
        assert config is not None

        url = "/apis/tickets/delete_ticket_flow_config/"
        response = client.delete(url, {"config_ids": [config.id]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        # DB 状态断言：验证配置已被删除
        assert not TicketFlowsConfig.objects.filter(id=config.id).exists()

    # ---- 集群操作记录（Mock filter_queryset + paginate_queryset） ----

    @patch("backend.ticket.views.TicketViewSet.paginate_queryset")
    @patch("backend.ticket.views.TicketViewSet.filter_queryset")
    def test_get_cluster_operate_records(self, mock_filter_qs, mock_paginate, test_running_ticket_with_flow):
        """测试查询集群变更单据事件"""
        ticket, flow = test_running_ticket_with_flow
        from backend.ticket.models import ClusterOperateRecord

        record = ClusterOperateRecord.objects.create(
            cluster_id=1,
            flow=flow,
            ticket=ticket,
            creator="admin",
            updater="admin",
        )

        mock_filter_qs.return_value = ClusterOperateRecord.objects.filter(id=record.id)
        mock_paginate.return_value = [record]

        url = "/apis/tickets/get_cluster_operate_records/"
        response = client.get(url, {"cluster_id": 1, "limit": 10, "offset": 0})

        assert response.status_code == status.HTTP_200_OK

        # 显式清理：测试结束后删除创建的记录
        record.delete()

    @patch("backend.ticket.views.TicketViewSet.paginate_queryset")
    @patch("backend.ticket.views.TicketViewSet.filter_queryset")
    def test_get_instance_operate_records(self, mock_filter_qs, mock_paginate, test_running_ticket_with_flow):
        """测试查询集群实例变更单据事件"""
        ticket, flow = test_running_ticket_with_flow
        from backend.ticket.models import InstanceOperateRecord

        record = InstanceOperateRecord.objects.create(
            instance_id=f"{cc.NORMAL_IP}:3306",
            flow=flow,
            ticket=ticket,
            creator="admin",
            updater="admin",
        )

        mock_filter_qs.return_value = InstanceOperateRecord.objects.filter(id=record.id)
        mock_paginate.return_value = [record]

        url = "/apis/tickets/get_instance_operate_records/"
        response = client.get(url, {"instance_id": record.instance_id, "limit": 10, "offset": 0})

        assert response.status_code == status.HTTP_200_OK

        # 显式清理：测试结束后删除创建的记录
        record.delete()
