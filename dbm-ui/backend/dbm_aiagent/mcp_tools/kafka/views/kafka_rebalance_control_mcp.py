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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_rebalance_control import (
    get_rebalance_progress,
    resume_rebalance_auto_throttle,
    set_rebalance_throttle,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_rebalance_control import (
    GetRebalanceProgressInputSerializer,
    GetRebalanceProgressOutputSerializer,
    ResumeAutoThrottleInputSerializer,
    ResumeAutoThrottleOutputSerializer,
    SetRebalanceThrottleInputSerializer,
    SetRebalanceThrottleOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Kafka Rebalance 单据控制 MCP - 查询/控制 Kafka rebalance 单据的执行进度与限速，
跟kafka-toolbox（远程执行Kafka CLI命令，输入是cluster_domain）不是同一类工具：
这里输入是ticket_id，数据来源是DBM Ticket + dbactuator状态文件，属于单据执行状态查询/控制。
"""


class KafkaRebalanceControlMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询Kafka rebalance单据的执行进度和当前限速。"
                "返回当前处理的topic、已完成/总数/百分比、执行状态(pending/in_progress/completed/failed)、"
                "当前限速值，单位MiB/s（1024x1024字节/秒）。参数：ticket_id（rebalance单据ID）"
            )
        ),
        request_slz=GetRebalanceProgressInputSerializer,
        response_slz=GetRebalanceProgressOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_REBALANCE_CONTROL],
        name_prefix="kafka_rebalance_control",
    )
    def get_rebalance_progress(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_rebalance_progress(ticket_id=validated_params["ticket_id"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "人工设置Kafka rebalance单据的限速，并切换为人工控制模式（sidecar自动调速会暂停，"
                "直到调用resume_rebalance_auto_throttle恢复）。只能对状态为in_progress的单据操作。"
                "参数：ticket_id（rebalance单据ID），throttle_mib_s（限速值，单位MiB/s，即1024x1024字节/秒）"
            )
        ),
        request_slz=SetRebalanceThrottleInputSerializer,
        response_slz=SetRebalanceThrottleOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_REBALANCE_CONTROL],
        name_prefix="kafka_rebalance_control",
    )
    def set_rebalance_throttle(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = set_rebalance_throttle(
            ticket_id=validated_params["ticket_id"],
            throttle_mib_s=validated_params["throttle_mib_s"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "恢复Kafka rebalance单据的自动调速（取消人工限速设置）。"
                "不会立即调整限速，交由sidecar在下一轮检查（最多2分钟内）按带宽利用率自动调整。"
                "只能对状态为in_progress的单据操作。参数：ticket_id（rebalance单据ID）"
            )
        ),
        request_slz=ResumeAutoThrottleInputSerializer,
        response_slz=ResumeAutoThrottleOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_REBALANCE_CONTROL],
        name_prefix="kafka_rebalance_control",
    )
    def resume_rebalance_auto_throttle(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = resume_rebalance_auto_throttle(ticket_id=validated_params["ticket_id"])
        return Response(result)
