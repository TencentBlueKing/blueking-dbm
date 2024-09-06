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
from collections import Counter
from functools import reduce
from typing import Dict, List

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
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import PaginatedResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
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
    FLOW_NOT_EXECUTE_STATUS,
    TICKET_RUNNING_STATUS,
    TICKET_TODO_STATUS,
    TODO_RUNNING_STATUS,
    CountType,
    FlowType,
    TicketType,
    TodoType,
)
from backend.ticket.contexts import TicketContext
from backend.ticket.exceptions import TicketDuplicationException
from backend.ticket.filters import ClusterOpRecordListFilter, InstanceOpRecordListFilter, TicketListFilter
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.handler import TicketHandler
from backend.ticket.models import ClusterOperateRecord, Flow, InstanceOperateRecord, Ticket, TicketFlowsConfig
from backend.ticket.serializers import (
    BatchTicketOperateSerializer,
    BatchTodoOperateSerializer,
    ClusterModifyOpSerializer,
    CreateTicketFlowConfigSerializer,
    DeleteTicketFlowConfigSerializer,
    FastCreateCloudComponentSerializer,
    GetInnerFlowSerializer,
    GetNodesSLZ,
    InstanceModifyOpSerializer,
    ListTicketStatusSerializer,
    QueryTicketFlowDescribeSerializer,
    RetryFlowSLZ,
    RevokeFlowSLZ,
    RevokeTicketSLZ,
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

TICKET_TAG = "ticket"


class TicketViewSet(viewsets.AuditedModelViewSet):
    """
    单据视图
    """

    queryset = Ticket.objects.all().prefetch_related("todo_of_ticket")
    serializer_class = TicketSerializer
    filter_class = TicketListFilter
    pagination_class = AuditedLimitOffsetPagination

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
        elif self.action in ["process_todo", "batch_process_todo", "batch_process_ticket"]:
            return []
        # 其他非敏感GET接口，不鉴权
        elif self.action in [
            "list",
            "flow_types",
            "get_nodes",
            "get_tickets_count",
            "query_ticket_flow_describe",
            "list_ticket_status",
            "get_inner_flow_infos",
            "revoke_ticket",
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

    @classmethod
    def _get_self_manage_tickets(cls, user):
        # 超级管理员返回所有单据
        if user.username in env.ADMIN_USERS or user.is_superuser:
            return Ticket.objects.all()
        # 获取user管理的单据合集
        manage_filters = [
            Q(group=manage.db_type) & Q(bk_biz_id=manage.bk_biz_id) if manage.bk_biz_id else Q(group=manage.db_type)
            for manage in DBAdministrator.objects.filter(users__contains=user.username)
        ]
        ticket_filter = Q(creator=user.username) | reduce(operator.or_, manage_filters or [Q()])
        return Ticket.objects.filter(ticket_filter)

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
            qs = Ticket.objects.filter(creator=username)
        # 返回自己管理的组件单据
        else:
            qs = self._get_self_manage_tickets(self.request.user)
        return qs

    def get_serializer_context(self):
        context = super(TicketViewSet, self).get_serializer_context()
        if self.action == "retrieve":
            context["ticket_ctx"] = TicketContext(ticket=self.get_object())
        else:
            context["ticket_ctx"] = TicketContext()
        return context

    @staticmethod
    def _verify_influxdb_duplicate_ticket(ticket_type, details, user, active_tickets):
        current_instances = InfluxdbTicketFlowBuilderPatchMixin.get_instances(ticket_type, details)
        for ticket in active_tickets:
            active_instances = ticket.details["instances"]
            duplicate_ids = list(set(active_instances).intersection(current_instances))
            if duplicate_ids:
                raise TicketDuplicationException(
                    context=_("实例{}已存在相同类型的单据[{}]正在运行，请确认是否重复提交").format(duplicate_ids, ticket.id),
                    data={"duplicate_instance_ids": duplicate_ids, "duplicate_ticket_id": ticket.id},
                )

    def verify_duplicate_ticket(self, ticket_type, details, user):
        """校验是否重复提交"""
        active_tickets = self.get_queryset().filter(
            ticket_type=ticket_type, status__in=TICKET_RUNNING_STATUS, creator=user
        )

        # influxdb 相关操作单独适配，这里暂时没有找到更好的写法，唯一的改进就是创建单据时，会提前提取出对比内容，比如instances
        # TODO: 后续这段逻辑待删除，influxdb已经弃用
        if ticket_type in TicketType.get_ticket_type_by_db(DBType.InfluxDB):
            self._verify_influxdb_duplicate_ticket(ticket_type, details, user, active_tickets)
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
            self.verify_duplicate_ticket(ticket_type, self.request.data["details"], self.request.user.username)

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
    @action(methods=["GET"], detail=False, serializer_class=ListTicketStatusSerializer, filter_class=None)
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

    @common_swagger_auto_schema(
        operation_summary=_("单据终止"),
        request_body=RevokeTicketSLZ(),
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RevokeTicketSLZ)
    def revoke_ticket(self, request, *args, **kwargs):
        ticket_ids = self.params_validate(self.get_serializer_class())["ticket_ids"]
        TicketHandler.revoke_ticket(ticket_ids, operator=request.user.username)
        return Response()

    @swagger_auto_schema(
        operation_summary=_("获取单据类型列表"),
        query_serializer=TicketTypeSLZ(),
        responses={status.HTTP_200_OK: TicketTypeResponseSLZ(many=True)},
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, filter_class=None, pagination_class=None, serializer_class=TicketTypeSLZ)
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

        return Response(TodoSerializer(ticket.todo_of_ticket.all(), many=True).data)

    @common_swagger_auto_schema(
        operation_summary=_("待办单据数"),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, filter_class=None, pagination_class=None)
    def get_tickets_count(self, request, *args, **kwargs):
        """
        获取单据的数量，目前需要获取
        - 我的申请
        - (代办)待我审批、待我确认，待我补货
        - 我的已办
        - 我负责的业务
        """
        user = request.user.username
        tickets = self._get_self_manage_tickets(request.user)
        count_map = {count_type: 0 for count_type in CountType.get_values()}

        # 我负责的业务
        count_map[CountType.SELF_MANAGE] = tickets.count()
        # 我的申请
        count_map[CountType.MY_APPROVE] = tickets.filter(creator=user).count()
        # 我的代办
        todo_status = (
            tickets.filter(
                status__in=TICKET_TODO_STATUS,
                todo_of_ticket__operators__contains=user,
                todo_of_ticket__status__in=TODO_RUNNING_STATUS,
            )
            .distinct()
            .values_list("status", flat=True)
        )
        for sts, count in Counter(todo_status).items():
            sts = CountType.INNER_TODO.value if sts == "RUNNING" else sts
            count_map[sts] = count
        # 我的已办
        count_map[CountType.DONE] = tickets.filter(todo_of_ticket__done_by=user).count()

        return Response(count_map)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群变更单据事件"),
        tags=[TICKET_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=ClusterModifyOpSerializer,
        queryset=ClusterOperateRecord.objects.select_related("ticket").order_by("-create_at"),
        filter_class=ClusterOpRecordListFilter,
    )
    def get_cluster_operate_records(self, request, *args, **kwargs):
        op_records_page_qs = self.paginate_queryset(self.filter_queryset(self.queryset))
        op_records_page_data = self.serializer_class(op_records_page_qs, many=True).data
        return self.get_paginated_response(data=op_records_page_data)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群实例变更单据事件"),
        tags=[TICKET_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=InstanceModifyOpSerializer,
        queryset=InstanceOperateRecord.objects.select_related("ticket").order_by("-create_at"),
        filter_class=InstanceOpRecordListFilter,
    )
    def get_instance_operate_records(self, request, *args, **kwargs):
        op_records_page_qs = self.paginate_queryset(self.filter_queryset(self.queryset))
        op_records_page_data = self.serializer_class(op_records_page_qs, many=True).data
        return self.get_paginated_response(data=op_records_page_data)

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
        filter_class=None,
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
        data = self.params_validate(self.get_serializer_class())
        user = request.user.username
        return Response(TicketHandler.batch_process_todo(user=user, **data))

    @swagger_auto_schema(
        operation_summary=_("批量单据待办处理"),
        request_body=BatchTicketOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer(many=True)},
        tags=[TICKET_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchTicketOperateSerializer)
    def batch_process_ticket(self, request, *args, **kwargs):
        """
        批量处理单据的待办，处理单据的第一个todo
        根据todo的类型可以触发不同的factor函数
        """
        data = self.params_validate(self.get_serializer_class())
        user = request.user.username

        tickets = Ticket.objects.prefetch_related("todo_of_ticket").filter(id__in=data["ticket_ids"])
        # 找到单据第一个代办（排除INNER_APPROVE，这是任务流程的人工确认节点产生的，不允许在单据维度操作）
        running_todos = [
            ticket.todo_of_ticket.exclude(type=TodoType.INNER_APPROVE).filter(status__in=TODO_RUNNING_STATUS).first()
            for ticket in tickets
        ]
        operations = [{"todo_id": todo.id, "params": data["params"]} for todo in running_todos if todo]

        return Response(TicketHandler.batch_process_todo(user=user, action=data["action"], operations=operations))

    @swagger_auto_schema(
        operation_summary=_("获取单据关联任务流程信息"),
        query_serializer=GetInnerFlowSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetInnerFlowSerializer, filter_class=None)
    def get_inner_flow_infos(self, request, *args, **kwargs):
        """
        获取单据关联后台任务的信息
        """
        ticket_ids = self.params_validate(self.get_serializer_class())["ticket_ids"].split(",")
        inner_flows = Flow.objects.filter(flow_type=FlowType.INNER_FLOW, ticket_id__in=ticket_ids).values(
            "ticket_id", "flow_obj_id", "flow_alias", "err_msg", "status"
        )
        ticket__inner_flow_map: Dict[int, List] = {int(t_id): [] for t_id in ticket_ids}
        for flow in inner_flows:
            # 快速判断流程树是否存在：有root_id，不包含error_msg，并且流程状态是执行过
            has_tree = bool(
                flow["flow_obj_id"] and not flow["err_msg"] and flow["status"] not in FLOW_NOT_EXECUTE_STATUS
            )
            flow_info = {"flow_id": flow["flow_obj_id"], "flow_alias": flow["flow_alias"], "pipeline_tree": has_tree}
            # 默认只将产生过pipeline tree的返回给前端
            if has_tree:
                ticket__inner_flow_map[flow["ticket_id"]].append(flow_info)
        return Response(ticket__inner_flow_map)
