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
import operator
from functools import reduce

from django.db import transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import PaginatedResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.configuration.models import DBAdministrator
from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import RejectPermission, ResourceActionPermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterDetailPermission, InstanceDetailPermission
from backend.iam_app.handlers.drf_perm.ticket import (
    BatchApprovalPermission,
    create_ticket_permission,
    ticket_flows_config_permission,
)
from backend.iam_app.handlers.permission import Permission
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import InfluxdbTicketFlowBuilderPatchMixin, fetch_cluster_ids
from backend.ticket.constants import (
    TODO_DONE_STATUS,
    CountType,
    OperateNodeActionType,
    TicketStatus,
    TicketType,
    TodoStatus,
)
from backend.ticket.contexts import TicketContext
from backend.ticket.exceptions import TicketDuplicationException
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.handler import TicketHandler
from backend.ticket.models import ClusterOperateRecord, InstanceOperateRecord, Ticket, TicketFlowsConfig, Todo
from backend.ticket.serializers import (
    BatchApprovalSerializer,
    BatchTodoOperateSerializer,
    ClusterModifyOpSerializer,
    CountTicketSLZ,
    CreateTicketFlowConfigSerializer,
    DeleteTicketFlowConfigSerializer,
    FastCreateCloudComponentSerializer,
    GetNodesSLZ,
    GetTodosSLZ,
    InstanceModifyOpSerializer,
    ListTicketStatusSerializer,
    QueryTicketFlowDescribeSerializer,
    RetryFlowSLZ,
    RevokeFlowSLZ,
    SensitiveTicketSerializer,
    TicketFlowDescribeSerializer,
    TicketFlowSerializer,
    TicketSerializer,
    TicketTypeResponseSLZ,
    TicketTypeSLZ,
    TodoOperateSerializer,
    TodoSerializer,
    UpdateTicketFlowConfigSerializer,
)
from backend.ticket.todos import TodoActorFactory
from backend.utils.batch_request import request_multi_thread

TICKET_TAG = "ticket"


class TicketViewSet(viewsets.AuditedModelViewSet):
    """
    单据视图
    """

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    # filter_class = TicketListFilter
    filter_fields = {
        "id": ["exact", "in"],
        "bk_biz_id": ["exact"],
        "ticket_type": ["exact", "in"],
        "status": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "creator": ["exact"],
    }

    def _get_custom_permissions(self):
        # 创建单据，关联单据类型的动作
        if self.action == "create":
            return create_ticket_permission(self.request.data["ticket_type"])
        if self.action == "batch_approval":
            return [BatchApprovalPermission()]
        # 创建敏感单据，只允许通过jwt校验的用户访问(warning: 这个网关接口授权需谨慎)
        if self.action == "create_sensitive_ticket":
            permission_class = [] if self.request.is_bk_jwt() else [RejectPermission()]
            return permission_class
        # 查看集群/实例变更条件，关联集群详情
        elif self.action == "get_cluster_operate_records":
            return [ClusterDetailPermission()]
        elif self.action == "get_instance_operate_records":
            return [InstanceDetailPermission()]
        # 单据详情，关联单据查看动作
        elif self.action in ["retrieve", "flows", "retry_flow", "revoke_flow"]:
            instance_getter = lambda request, view: [request.parser_context["kwargs"]["pk"]]  # noqa
            return [ResourceActionPermission([ActionEnum.TICKET_VIEW], ResourceEnum.TICKET, instance_getter)]
        # 单据流程设置，关联单据流程设置动作
        elif self.action in ["update_ticket_flow_config", "create_ticket_flow_config", "delete_ticket_flow_config"]:
            return ticket_flows_config_permission(self.action, self.request)
        # 对于处理todo的接口，可以不用鉴权，todo本身会判断是否是确认人
        elif self.action in ["process_todo", "batch_process_todo"]:
            return []
        # 其他非敏感GET接口，不鉴权
        elif self.action in [
            "list",
            "flow_types",
            "get_nodes",
            "get_todo_tickets",
            "get_tickets_count",
            "query_ticket_flow_describe",
            "list_ticket_status",
        ]:
            return []
        # 回调和处理无需鉴权
        elif self.action in ["callback"]:
            return []

        return [RejectPermission()]

    @classmethod
    def _get_login_exempt_view_func(cls):
        # 需要豁免的接口方法与名字
        return {"post": [cls.callback.__name__], "put": [], "get": [], "delete": []}

    def get_queryset(self):
        """
        单据queryset规则--针对list：
        1. self_manage=0 只返回自己管理的单据
        2. self_manage=1，则返回自己管理组件的单据，如果是管理员则返回所有单据
        """
        if self.action != "list" or "self_manage" not in self.request.query_params:
            return super().get_queryset()

        username = self.request.user.username
        self_manage = int(self.request.query_params["self_manage"])
        # 只返回自己创建的单据
        if self_manage == 0:
            return Ticket.objects.filter(creator=username)
        # 超级管理员返回所有单据
        if username in env.ADMIN_USERS or self.request.user.is_superuser:
            return Ticket.objects.all()
        # 返回自己管理的组件单据
        manage_filters = [
            Q(group=manage.db_type) & Q(bk_biz_id=manage.bk_biz_id) if manage.bk_biz_id else Q(group=manage.db_type)
            for manage in DBAdministrator.objects.filter(users__contains=username)
        ]
        ticket_filter = Q(creator=username) | reduce(operator.or_, manage_filters or [Q()])
        return Ticket.objects.filter(ticket_filter)

    def get_serializer_context(self):
        context = super(TicketViewSet, self).get_serializer_context()
        if self.action == "retrieve":
            context["ticket_ctx"] = TicketContext(ticket=self.get_object())
        else:
            context["ticket_ctx"] = TicketContext()
        return context

    def _verify_duplicate_ticket(self, ticket_type, details, user):
        """校验是否重复提交"""

        active_tickets = self.get_queryset().filter(ticket_type=ticket_type, status=TicketStatus.RUNNING, creator=user)

        # influxdb 相关操作单独适配，这里暂时没有找到更好的写法，唯一的改进就是创建单据时，会提前提取出对比内容，比如instances
        if ticket_type in [
            TicketType.INFLUXDB_ENABLE,
            TicketType.INFLUXDB_DISABLE,
            TicketType.INFLUXDB_REBOOT,
            TicketType.INFLUXDB_DESTROY,
            TicketType.INFLUXDB_REPLACE,
        ]:
            current_instances = InfluxdbTicketFlowBuilderPatchMixin.get_instances(ticket_type, details)
            for ticket in active_tickets:
                active_instances = ticket.details["instances"]
                duplicate_ids = list(set(active_instances).intersection(current_instances))
                if duplicate_ids:
                    raise TicketDuplicationException(
                        context=_("实例{}已存在相同类型的单据[{}]正在运行，请确认是否重复提交").format(duplicate_ids, ticket.id),
                        data={"duplicate_instance_ids": duplicate_ids, "duplicate_ticket_id": ticket.id},
                    )
            return

        cluster_ids = fetch_cluster_ids(details=details)
        for ticket in active_tickets:
            active_cluster_ids = fetch_cluster_ids(details=ticket.details)
            duplicate_ids = list(set(active_cluster_ids).intersection(cluster_ids))
            if duplicate_ids:
                raise TicketDuplicationException(
                    context=_("集群{}已存在相同类型的单据[{}]正在运行，请确认是否重复提交").format(duplicate_ids, ticket.id),
                    data={"duplicate_cluster_ids": duplicate_ids, "duplicate_ticket_id": ticket.id},
                )

    def perform_create(self, serializer):
        ticket_type = self.request.data["ticket_type"]
        ignore_duplication = self.request.data.get("ignore_duplication") or False
        # 如果不允许忽略重复提交，则进行校验
        if not ignore_duplication:
            self._verify_duplicate_ticket(ticket_type, self.request.data["details"], self.request.user.username)

        with transaction.atomic():
            # 设置单据类别 TODO: 这里会请求两次数据库，是否考虑group参数让前端传递
            ticket = super().perform_create(serializer)
            serializer.save(group=BuilderFactory.get_builder_cls(ticket_type).group)
            # 初始化builder类
            builder = BuilderFactory.create_builder(ticket)
            builder.patch_ticket_detail()
            builder.init_ticket_flows()

        TicketFlowManager(ticket=ticket).run_next_flow()

    @swagger_auto_schema(
        operation_summary=_("单据详情"),
        responses={status.HTTP_200_OK: TicketSerializer(label=_("单据详情"))},
        tags=[TICKET_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        """单据实例详情"""

        # 标记单据是否已读(这个已读属性只用于与todo代办联动，正常可以不管)
        is_reviewed = int(request.query_params.get("is_reviewed") or 0)
        if is_reviewed:
            instance = self.get_object()
            instance.is_reviewed = int(is_reviewed)
            instance.save()

        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("单据列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[TICKET_TAG],
    )
    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=[ActionEnum.TICKET_VIEW],
        resource_meta=ResourceEnum.TICKET,
        always_allowed=lambda d: d.pop("skip_iam", False),
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        # 补充单据关联信息
        resp.data["results"] = TicketHandler.add_related_object(resp.data["results"])
        # 如果是查询自身单据(self_manage)，则不进行鉴权
        skip_iam = "self_manage" in request.query_params
        resp.data["results"] = [{"skip_iam": skip_iam, **t} for t in resp.data["results"]]
        return resp

    @common_swagger_auto_schema(
        operation_summary=_("查询单据状态"),
        query_serializer=ListTicketStatusSerializer(),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListTicketStatusSerializer, filter_fields=None)
    def list_ticket_status(self, request, *args, **kwargs):
        ticket_ids = self.params_validate(self.get_serializer_class())["ticket_ids"].split(",")
        ticket_status_map = {ticket.id: ticket.status for ticket in Ticket.objects.filter(id__in=ticket_ids)}
        return Response(ticket_status_map)

    @common_swagger_auto_schema(
        operation_summary=_("创建单据"),
        responses={status.HTTP_200_OK: TicketSerializer(label=_("创建单据"))},
        tags=[TICKET_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("创建单据(允许创建敏感单据)"),
        request_body=SensitiveTicketSerializer(),
        responses={status.HTTP_200_OK: SensitiveTicketSerializer(label=_("创建单据(允许创建敏感单据)"))},
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SensitiveTicketSerializer)
    def create_sensitive_ticket(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("获取单据流程"),
        responses={status.HTTP_200_OK: TicketFlowSerializer(label=_("流程信息"), many=True)},
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=TicketFlowSerializer)
    def flows(self, request, *args, **kwargs):
        """补充todo列表"""
        ticket = self.get_object()
        serializer = self.get_serializer(ticket.flows, many=True)
        return Response(serializer.data)

    @common_swagger_auto_schema(
        operation_summary=_("单据回调"),
        request_body=serializers.Serializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=True, permission_classes=[AllowAny])
    def callback(self, request, pk):
        ticket = Ticket.objects.get(id=pk)
        manager = TicketFlowManager(ticket=ticket)
        manager.run_next_flow()
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("单据流程重试"),
        request_body=RetryFlowSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=RetryFlowSLZ)
    def retry_flow(self, request, pk):
        validated_data = self.params_validate(self.get_serializer_class())
        TicketHandler.operate_flow(ticket_id=pk, flow_id=validated_data["flow_id"], func="retry")
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("单据流程终止"),
        request_body=RevokeFlowSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=RetryFlowSLZ)
    def revoke_flow(self, request, pk):
        validated_data = self.params_validate(self.get_serializer_class())
        user = self.request.user.username
        TicketHandler.operate_flow(ticket_id=pk, flow_id=validated_data["flow_id"], func="revoke", operator=user)
        return Response()

    @swagger_auto_schema(
        operation_summary=_("获取单据类型列表"),
        query_serializer=TicketTypeSLZ(),
        responses={status.HTTP_200_OK: TicketTypeResponseSLZ(many=True)},
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, filter_fields=None, pagination_class=None, serializer_class=TicketTypeSLZ)
    def flow_types(self, request, *args, **kwargs):
        is_apply = self.params_validate(self.get_serializer_class())["is_apply"]
        ticket_type_list = []
        for choice in TicketType.get_choices():
            if not is_apply or choice[0] in BuilderFactory.apply_ticket_type:
                ticket_type_list.append({"key": choice[0], "value": choice[1]})
        return Response(ticket_type_list)

    @common_swagger_auto_schema(
        operation_summary=_("节点列表"),
        query_serializer=GetNodesSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=GetNodesSLZ)
    def get_nodes(self, request, *args, **kwargs):
        """从上架单中获取节点信息"""

        ticket = self.get_object()

        validated_data = self.params_validate(self.get_serializer_class())
        role, keyword = validated_data["role"], validated_data.get("keyword")
        role_nodes = ticket.details["nodes"].get(role, [])
        instances_hash = {role_node["bk_host_id"]: role_node.get("instance_num", 1) for role_node in role_nodes}
        role_host_ids = [role_node["bk_host_id"] for role_node in role_nodes]

        if not role_host_ids:
            return Response([])

        hosts = ResourceQueryHelper.search_cc_hosts(role_host_ids, keyword)

        # 补充实例数，默认为1
        for host in hosts:
            host["instance_num"] = instances_hash.get(host["bk_host_id"])

        return Response(hosts)

    @common_swagger_auto_schema(
        operation_summary=_("待办单据列表"),
        query_serializer=GetTodosSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetTodosSLZ)
    def get_todo_tickets(self, request, *args, **kwargs):
        """待办视图单据列表"""

        # 获取我的待办
        validated_data = self.params_validate(self.get_serializer_class())
        todo_status = validated_data.get("todo_status")

        my_todos = Todo.objects.filter(operators__contains=request.user.username)

        # 状态筛选：已处理/未处理
        if todo_status in TODO_DONE_STATUS:
            my_todos = my_todos.filter(status__in=TODO_DONE_STATUS)
        elif todo_status:
            my_todos = my_todos.filter(status=todo_status)

        # 复用全局过滤器
        tickets = self.filter_queryset(self.get_queryset())

        # 关联查询单据
        my_todo_tickets = tickets.filter(id__in=my_todos.values_list("ticket_id"))
        context = self.get_serializer_context()

        # 分页处理
        page = self.paginate_queryset(my_todo_tickets)
        if page is not None:
            serializer = TicketSerializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)

        serializer = TicketSerializer(page, many=True, context=context)
        serializer.data["results"] = TicketHandler.add_related_object(serializer.data["results"])
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=_("待办处理"),
        request_body=TodoOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer()},
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=TodoOperateSerializer)
    def process_todo(self, request, *args, **kwargs):
        """
        处理待办: 返回处理后的待办列表
        """

        ticket = self.get_object()

        validated_data = self.params_validate(self.get_serializer_class())

        todo = ticket.todo_of_ticket.get(id=validated_data["todo_id"])
        TodoActorFactory.actor(todo).process(request.user.username, validated_data["action"], validated_data["params"])

        # 如果是数据迁移单据，更改迁移记录状态信息
        if ticket.ticket_type in [TicketType.SQLSERVER_INCR_MIGRATE, TicketType.SQLSERVER_FULL_MIGRATE]:
            dts = SqlserverDtsInfo.objects.get(ticket_id=ticket.id)
            dts.status = DtsStatus.Terminated.value
            dts.save()
        return Response(TodoSerializer(ticket.todo_of_ticket.all(), many=True).data)

    @common_swagger_auto_schema(
        operation_summary=_("待办单据数"),
        query_serializer=CountTicketSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=CountTicketSLZ)
    def get_tickets_count(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        count_type = validated_data.get("count_type")

        # 待办单数量
        if count_type == CountType.MY_TODO:
            my_todos = Todo.objects.filter(status=TodoStatus.TODO, operators__contains=request.user.username)
            tickets = self.filter_queryset(self.get_queryset())
            my_tickets = tickets.filter(id__in=my_todos.values_list("ticket_id"))
        else:
            # 申请单数量
            my_tickets = Ticket.objects.filter(
                creator=request.user.username, status__in=[TicketStatus.RUNNING, TicketStatus.PENDING]
            )

        return Response(my_tickets.count())

    @common_swagger_auto_schema(
        operation_summary=_("查询集群变更单据事件"),
        query_serializer=ClusterModifyOpSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ClusterModifyOpSerializer)
    def get_cluster_operate_records(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        op_filters = Q(cluster_id=validated_data["cluster_id"])
        if validated_data.get("start_time"):
            op_filters &= Q(create_at__gte=validated_data.get("start_time"))

        if validated_data.get("end_time"):
            op_filters &= Q(create_at__lte=validated_data.get("end_time"))

        if validated_data.get("op_type"):
            op_filters &= Q(ticket__ticket_type=validated_data.get("op_type"))

        if validated_data.get("op_status"):
            op_filters &= Q(ticket__status=validated_data.get("op_status"))

        op_records = ClusterOperateRecord.objects.select_related("ticket").filter(op_filters).order_by("-create_at")
        op_records_info = [
            {
                "create_at": record.create_at,
                "op_type": TicketType.get_choice_label(record.ticket.ticket_type),
                "op_status": record.ticket.status,
                "ticket_id": record.ticket.id,
                "creator": record.creator,
            }
            for record in op_records
        ]
        op_records_page = self.paginate_queryset(op_records_info)
        return self.get_paginated_response(op_records_page)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群实例变更单据事件"),
        query_serializer=InstanceModifyOpSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=InstanceModifyOpSerializer)
    def get_instance_operate_records(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        op_filters = Q(instance_id=validated_data["instance_id"])
        if validated_data.get("start_time"):
            op_filters &= Q(create_at__gte=validated_data.get("start_time"))

        if validated_data.get("end_time"):
            op_filters &= Q(create_at__lte=validated_data.get("end_time"))

        if validated_data.get("op_type"):
            op_filters &= Q(ticket__ticket_type=validated_data.get("op_type"))

        if validated_data.get("op_status"):
            op_filters &= Q(ticket__status=validated_data.get("op_status"))

        op_records = InstanceOperateRecord.objects.select_related("ticket").filter(op_filters).order_by("-create_at")
        op_records_info = [
            {
                "create_at": record.create_at,
                "op_type": TicketType.get_choice_label(record.ticket.ticket_type),
                "op_status": record.ticket.status,
                "ticket_id": record.ticket.id,
                "creator": record.creator,
            }
            for record in op_records
        ]
        op_records_page = self.paginate_queryset(op_records_info)
        return self.get_paginated_response(op_records_page)

    @swagger_auto_schema(
        operation_summary=_("查询可编辑单据流程描述"),
        query_serializer=QueryTicketFlowDescribeSerializer(),
        responses={status.HTTP_200_OK: TicketFlowDescribeSerializer},
        tags=[TICKET_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=QueryTicketFlowDescribeSerializer,
        filter_fields=None,
        pagination_class=None,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["db_type"],
        actions=[ActionEnum.GLOBAL_TICKET_CONFIG_SET],
        resource_meta=ResourceEnum.DBTYPE,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: {ResourceEnum.DBTYPE.id: d["db_type"], ResourceEnum.BUSINESS.id: d.get("bk_biz_id")},
        actions=[ActionEnum.BIZ_TICKET_CONFIG_SET],
        resource_meta=[ResourceEnum.DBTYPE, ResourceEnum.BUSINESS],
    )
    def query_ticket_flow_describe(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(TicketHandler.query_ticket_flows_describe(**data))

    @swagger_auto_schema(
        operation_summary=_("修改可编辑的单据流程规则"),
        request_body=UpdateTicketFlowConfigSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateTicketFlowConfigSerializer)
    def update_ticket_flow_config(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        TicketHandler.update_ticket_flow_config(**data, operator=request.user.username)
        return Response()

    @swagger_auto_schema(
        operation_summary=_("创建单据流程规则"),
        request_body=CreateTicketFlowConfigSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CreateTicketFlowConfigSerializer)
    def create_ticket_flow_config(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        TicketHandler.create_ticket_flow_config(**data, operator=request.user.username)
        return Response()

    @swagger_auto_schema(
        operation_summary=_("删除单据流程规则"),
        request_body=DeleteTicketFlowConfigSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteTicketFlowConfigSerializer)
    def delete_ticket_flow_config(self, request, *args, **kwargs):
        config_ids = self.params_validate(self.get_serializer_class())["config_ids"]
        TicketFlowsConfig.objects.filter(id__in=config_ids).delete()
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("快速部署云区域组件"),
        request_body=FastCreateCloudComponentSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=FastCreateCloudComponentSerializer)
    def fast_create_cloud_component(self, request, *args, **kwargs):
        """快速创建云区域组件 TODO: 目前部署方案暂支持两台, 后续可以拓展"""
        validated_data = self.params_validate(self.get_serializer_class())
        bk_cloud_id = validated_data["bk_cloud_id"]
        ips = validated_data["ips"]
        bk_biz_id = validated_data["bk_biz_id"]
        TicketHandler.fast_create_cloud_component_method(bk_biz_id, bk_cloud_id, ips, request.user.username)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("批量审批"),
        request_body=BatchApprovalSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchApprovalSerializer)
    def batch_approval(self, request, *args, **kwargs):
        """
        sns: 单号集合
        is_approved: 是否审批通过
        """
        data = self.params_validate(self.get_serializer_class())
        ticket_ids, is_approved = data["ticket_ids"], data["is_approved"]
        user, itsm_action = request.user.username, OperateNodeActionType.TRANSITION
        params_list = [
            {"ticket_id": ticket, "action": itsm_action, "is_approved": is_approved, "operator": user}
            for ticket in ticket_ids
        ]
        request_multi_thread(TicketHandler.approve_itsm_ticket, params_list)
        return Response()

    @swagger_auto_schema(
        operation_summary=_("批量待办处理"),
        request_body=BatchTodoOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer(many=True)},
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchTodoOperateSerializer)
    def batch_process_todo(self, request, *args, **kwargs):
        """
        批量处理待办: 返回处理后的待办列表
        """
        validated_data = self.params_validate(self.get_serializer_class())
        act = validated_data["action"]

        # 批量处理待办操作
        results = []
        for operation in validated_data["operations"]:
            todo_id = operation["todo_id"]
            params = operation["params"]
            todo = Todo.objects.get(id=todo_id)
            TodoActorFactory.actor(todo).process(request.user.username, act, params)
            results.append(todo)

        # 使用 TodoSerializer 序列化响应数据
        return Response(TodoSerializer(results, many=True).data)
