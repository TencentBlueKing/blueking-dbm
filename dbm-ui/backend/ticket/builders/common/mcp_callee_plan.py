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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.flow.engine.controller.base import BaseController
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    ParamValidateSerializerMixin,
    SkipToRepresentationMixin,
    TicketBaseValidateSerializerMixin,
)
from backend.ticket.constants import FlowRetryType, TicketType


class RegisterMcpCalleePlanDetailSerializer(
    TicketBaseValidateSerializerMixin, SkipToRepresentationMixin, ParamValidateSerializerMixin, serializers.Serializer
):
    plan_id = serializers.IntegerField()
    mcp_id = serializers.CharField()
    params = serializers.DictField()
    time_window_start = serializers.DateTimeField()
    time_window_end = serializers.DateTimeField()
    max_call_count = serializers.IntegerField()


class RegisterMcpCalleePlanFlowParamBuilder(builders.FlowParamBuilder):
    """MCP 执行计划注册参数构建器"""

    controller = BaseController.register_mcp_callee_plan


class BaseMcpCalleePlanFlowBuilder(TicketFlowBuilder):
    """MCP 执行计划注册单据流程的抽象基类。

    由于 DBM 当前的单据审批设计，单据必须绑定在某个 DBType 下才能正常走审批流程，
    因此无法实现一个公共的 MCP 计划注册单据。各 DB 类型需要继承此类并提供各自的 group 和 inner_flow_name。
    """

    serializer = RegisterMcpCalleePlanDetailSerializer
    inner_flow_builder = RegisterMcpCalleePlanFlowParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY

    default_need_itsm = True
    default_need_manual_confirm = False

    group: str = None
    inner_flow_name: str = None


@builders.BuilderFactory.register(TicketType.MYSQL_REGISTER_MCP_CALLEE_PLAN)
class MySQLMcpCalleePlanFlowBuilder(BaseMcpCalleePlanFlowBuilder):
    """
    大部分时候 TenDBHA, TenDBSingle, TenDBCluster 的 DBA 是同一个人
    所以这里就统一到 MySQL 下了, 不细分出多一个 TenDBCluster group 单据来
    """

    group = DBType.MySQL.value
    inner_flow_name = _("注册 MYSQL MCP 执行计划")
