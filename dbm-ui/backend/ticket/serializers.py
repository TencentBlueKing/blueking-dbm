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
from typing import Optional

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.bk_web.constants import LEN_MIDDLE
from backend.bk_web.serializers import AuditedSerializer, TranslationSerializerMixin
from backend.configuration.constants import DBType
from backend.ticket import mock_data
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import CountType, TicketStatus, TicketType, TodoStatus
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket, Todo
from backend.ticket.yasg_slz import todo_operate_example
from backend.utils.time import calculate_cost_time, strptime


class TicketDetailsSerializer(serializers.Serializer):
    def get_exact_serializer(self, ticket_type: Optional[str] = None):
        if not ticket_type:
            return serializers.Serializer()
        slz = BuilderFactory.get_serializer(ticket_type)

        # 更新上下文信息
        slz.context.update(self.context)
        slz.context.update({"ticket_type": ticket_type})
        slz.context.update({"bk_biz_id": self.context["request"].data.get("bk_biz_id")})
        return slz

    def get_context_ticket_type(self):
        return self.context["request"].data["ticket_type"]

    def validate(self, attrs):
        ticket_type = self.get_context_ticket_type()
        return self.get_exact_serializer(ticket_type).validate(attrs)

    def to_representation(self, instance):
        parent_instance = self.parent.instance
        ticket_type = "" if isinstance(parent_instance, list) else parent_instance.ticket_type
        return self.get_exact_serializer(ticket_type).to_representation(instance)

    def to_internal_value(self, data):
        ticket_type = data.get("ticket_type", None) or self.get_context_ticket_type()
        return self.get_exact_serializer(ticket_type).to_internal_value(data)


class TicketSerializer(AuditedSerializer, serializers.ModelSerializer):
    """
    单据序列化
    """

    # 基础信息
    id = serializers.IntegerField(help_text=_("单据ID"), read_only=True)
    ticket_type = serializers.ChoiceField(
        help_text=_("单据类型"), choices=TicketType.get_choices(), default=TicketType.MYSQL_SINGLE_APPLY
    )
    status = serializers.ChoiceField(help_text=_("状态"), choices=TicketStatus.get_choices(), read_only=True)
    remark = serializers.CharField(help_text=_("备注"), required=False, max_length=LEN_MIDDLE, allow_blank=True)
    # 默认使用MySQL序列化器，不同单据类型不同字段序列化
    group = serializers.CharField(help_text=_("单据分组类型"), required=False)
    details = TicketDetailsSerializer(help_text=_("单据详情"))
    # 额外补充展示字段
    ticket_type_display = serializers.SerializerMethodField(help_text=_("单据类型名称"))
    status_display = serializers.SerializerMethodField(help_text=_("状态名称"))
    cost_time = serializers.SerializerMethodField(help_text=_("耗时"))
    bk_biz_name = serializers.SerializerMethodField(help_text=_("业务名"))
    db_app_abbr = serializers.SerializerMethodField(help_text=_("业务英文缩写"))
    # 是否忽略重复提交
    ignore_duplication = serializers.BooleanField(
        help_text=_("是否忽略重复提交"), required=False, default=False, read_only=True
    )

    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = ("id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": mock_data.CREATE_TENDBHA_TICKET_DATA}

    def get_ticket_type_display(self, obj):
        return obj.get_ticket_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_cost_time(self, obj):
        if obj.status in [TicketStatus.PENDING, TicketStatus.RUNNING]:
            return calculate_cost_time(timezone.now(), obj.create_at)
        return calculate_cost_time(obj.update_at, obj.create_at)

    def get_bk_biz_name(self, obj):
        return self.context["ticket_ctx"].biz_name_map.get(obj.bk_biz_id) or obj.bk_biz_id

    def get_db_app_abbr(self, obj):
        return self.context["ticket_ctx"].app_abbr_map.get(obj.bk_biz_id) or ""


class TicketFlowSerializer(TranslationSerializerMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField(help_text=_("流程状态"))
    todos = serializers.SerializerMethodField(help_text=_("流程待办"))
    url = serializers.SerializerMethodField(help_text=_("跳转链接"))
    start_time = serializers.SerializerMethodField(help_text=_("开始时间"))
    end_time = serializers.SerializerMethodField(help_text=_("结束时间"))
    cost_time = serializers.SerializerMethodField(help_text=_("耗时"))
    flow_type_display = serializers.SerializerMethodField(help_text=_("流程类型显示名"))
    summary = serializers.SerializerMethodField(help_text=_("概览"))

    def to_representation(self, instance):
        self.ticket_flow = TicketFlowManager(ticket=instance.ticket).get_ticket_flow_cls(flow_type=instance.flow_type)(
            instance
        )
        return super().to_representation(instance)

    def get_todos(self, obj):
        return TodoSerializer(obj.todo_of_flow.all(), many=True).data

    def get_status(self, obj):
        return self.ticket_flow.status

    def get_url(self, obj):
        return self.ticket_flow.url

    def get_start_time(self, obj):
        return self.ticket_flow.start_time

    def get_end_time(self, obj):
        return self.ticket_flow.end_time

    def get_cost_time(self, obj):
        start_time = strptime(self.get_start_time(obj))
        end_time = strptime(self.get_end_time(obj))
        if self.get_status(obj) in [TicketStatus.PENDING, TicketStatus.RUNNING]:
            return calculate_cost_time(timezone.now(), start_time)
        return calculate_cost_time(end_time, start_time)

    def get_flow_type_display(self, obj):
        return obj.flow_alias or obj.get_flow_type_display()

    def get_summary(self, obj):
        return self.ticket_flow.summary

    @property
    def translated_fields(self):
        return ["flow_alias", "err_msg", "flow_type_display"]

    class Meta:
        model = Flow
        fields = "__all__"


class TodoSerializer(serializers.ModelSerializer):
    """
    单据序列化
    """

    operators = serializers.JSONField(help_text=_("待办人列表"))
    cost_time = serializers.SerializerMethodField(help_text=_("耗时"))

    def get_cost_time(self, obj):
        if obj.status in [TodoStatus.TODO, TodoStatus.RUNNING]:
            return calculate_cost_time(timezone.now(), obj.create_at)
        return calculate_cost_time(obj.done_at, obj.create_at)

    class Meta:
        model = Todo
        exclude = model.AUDITED_FIELDS


class TodoOperateSerializer(serializers.Serializer):
    """
    待办处理
    """

    todo_id = serializers.CharField(help_text=_("待办ID"))
    action = serializers.CharField(help_text=_("动作"))
    params = serializers.JSONField(help_text=_("动作参数"))

    class Meta:
        swagger_schema_fields = {"example": todo_operate_example}


class TicketTypeSLZ(serializers.Serializer):
    is_apply = serializers.BooleanField(help_text=_("是否是部署类单据"), required=False, default=False)


class TicketTypeResponseSLZ(serializers.Serializer):
    key = serializers.CharField(help_text="ID")
    value = serializers.CharField(help_text=_("名称"))


class GetNodesSLZ(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    role = serializers.CharField(help_text=_("角色"))
    keyword = serializers.CharField(help_text=_("关键字过滤"), required=False, allow_blank=True)


class RetryFlowSLZ(serializers.Serializer):
    flow_id = serializers.IntegerField(help_text=_("单据流程的ID"))


class GetTodosSLZ(serializers.Serializer):
    todo_status = serializers.ChoiceField(
        help_text=_("状态"), choices=TodoStatus.get_choices(), required=False, allow_blank=True
    )


class CountTicketSLZ(serializers.Serializer):
    count_type = serializers.ChoiceField(help_text=_("类型"), choices=CountType.get_choices(), default=CountType.MY_TODO)


class ClusterModifyOpSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    start_time = serializers.DateTimeField(help_text=_("查询起始时间"), required=False)
    end_time = serializers.DateTimeField(help_text=_("查询终止时间"), required=False)
    op_type = serializers.ChoiceField(help_text=_("操作类型"), choices=TicketType.get_choices(), required=False)
    op_status = serializers.ChoiceField(help_text=_("操作状态"), choices=TicketStatus.get_choices(), required=False)


class InstanceModifyOpSerializer(serializers.Serializer):
    instance_id = serializers.IntegerField(help_text=_("实例ID"))
    start_time = serializers.DateTimeField(help_text=_("查询起始时间"), required=False)
    end_time = serializers.DateTimeField(help_text=_("查询终止时间"), required=False)
    op_type = serializers.ChoiceField(help_text=_("操作类型"), choices=TicketType.get_choices(), required=False)
    op_status = serializers.ChoiceField(help_text=_("操作状态"), choices=TicketStatus.get_choices(), required=False)


class QueryTicketFlowDescribeSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("单据分组类型"), choices=DBType.get_choices())
    ticket_types = serializers.CharField(help_text=_("单据类型"), default=False)

    def validate(self, attrs):
        if attrs.get("ticket_types"):
            attrs["ticket_types"] = attrs["ticket_types"].split(",")
        return attrs


class UpdateTicketFlowConfigSerializer(serializers.Serializer):
    ticket_types = serializers.ListField(
        help_text=_("单据类型"), child=serializers.ChoiceField(choices=TicketType.get_choices())
    )
    configs = serializers.DictField(help_text=_("单据可配置项"))


class TicketFlowDescribeDetailSerializer(serializers.Serializer):
    flow_desc = serializers.ListField(help_text=_("单据流程描述"), child=serializers.CharField())
    db_type = serializers.ChoiceField(help_text=_("单据分组类型"), choices=DBType.get_choices())
    ticket_type = serializers.ChoiceField(help_text=_("单据类型"), choices=TicketType.get_choices())
    need_itsm = serializers.BooleanField(help_text=_("是否需要单据审批"))
    need_manual_confirm = serializers.BooleanField(help_text=_("是否需要人工确认"))


TicketFlowDescribeSerializer = serializers.ListSerializer(
    help_text=_("单据流程描述"), child=TicketFlowDescribeDetailSerializer()
)


class FastCreateCloudComponentSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("主机所在业务"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    ips = serializers.ListField(help_text=_("IP列表"), child=serializers.CharField())

    def validate(self, attrs):
        if len(attrs["ips"]) < 2:
            raise serializers.ValidationError(_("请至少提供两台机器来部署云区域组件"))

        return attrs
