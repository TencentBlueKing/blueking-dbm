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
from backend.dbm_aiagent.mcp_tools.pulsar.impl.pulsar_toolbox import (
    cluster_health_check,
    describe_topic,
    get_namespace_policies,
    list_brokers,
    list_namespaces,
    list_subscriptions,
    list_tenants,
    list_topics,
    topic_internal_stats,
)
from backend.dbm_aiagent.mcp_tools.pulsar.serializers.pulsar_toolbox import (
    ClusterHealthCheckOutputSerializer,
    DescribeTopicOutputSerializer,
    ListBrokersOutputSerializer,
    ListNamespacesInputSerializer,
    ListNamespacesOutputSerializer,
    ListSubscriptionsOutputSerializer,
    ListTenantsOutputSerializer,
    ListTopicsInputSerializer,
    ListTopicsOutputSerializer,
    NamespaceInputSerializer,
    NamespacePoliciesOutputSerializer,
    PulsarToolboxClusterInputSerializer,
    TopicInputSerializer,
    TopicInternalStatsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Pulsar 工具箱 MCP - 在 Pulsar 集群 broker 上远程执行 pulsar-admin 命令
- 只读：list_tenants, list_namespaces, list_topics, describe_topic, topic_internal_stats,
        list_subscriptions, get_namespace_policies, list_brokers, cluster_health_check
"""


class PulsarToolboxMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _("列出Pulsar集群所有租户(tenant)。" "Pulsar采用租户/namespace/topic三级结构，租户是最顶层。" "参数：cluster_domain（集群域名）")
        ),
        request_slz=PulsarToolboxClusterInputSerializer,
        response_slz=ListTenantsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def list_tenants(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_tenants(immute_domain=validated_params["cluster_domain"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("列出Pulsar租户下的所有namespace。" "参数：cluster_domain（集群域名），tenant（租户名称，如 public）")),
        request_slz=ListNamespacesInputSerializer,
        response_slz=ListNamespacesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def list_namespaces(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_namespaces(
            immute_domain=validated_params["cluster_domain"],
            tenant=validated_params["tenant"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _("列出Pulsar namespace下的所有topic。" "参数：cluster_domain（集群域名），namespace（格式 tenant/namespace，如 public/default）")
        ),
        request_slz=ListTopicsInputSerializer,
        response_slz=ListTopicsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def list_topics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_topics(
            immute_domain=validated_params["cluster_domain"],
            namespace=validated_params["namespace"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查看Pulsar topic统计信息，包括生产/消费速率、存储大小、各订阅的消息积压(backlog)、消费者连接情况。"
                "排查消费积压问题时优先使用该工具。"
                "参数：cluster_domain（集群域名），topic（完整名称，如 persistent://public/default/my-topic）"
            )
        ),
        request_slz=TopicInputSerializer,
        response_slz=DescribeTopicOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def describe_topic(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = describe_topic(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查看Pulsar topic内部存储状态，包括ledger分布、entry数量、游标位置。"
                "用于排查BookKeeper存储层问题。"
                "参数：cluster_domain（集群域名），topic（完整名称）"
            )
        ),
        request_slz=TopicInputSerializer,
        response_slz=TopicInternalStatsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def topic_internal_stats(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = topic_internal_stats(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("列出Pulsar topic的所有订阅(subscription)。" "参数：cluster_domain（集群域名），topic（完整名称）")),
        request_slz=TopicInputSerializer,
        response_slz=ListSubscriptionsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def list_subscriptions(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_subscriptions(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查看Pulsar namespace策略配置，包括消息保留策略(retention)、持久化策略(ensemble/write quorum/ack quorum)、限流配置、backlog配额。"
                "参数：cluster_domain（集群域名），namespace（格式 tenant/namespace）"
            )
        ),
        request_slz=NamespaceInputSerializer,
        response_slz=NamespacePoliciesOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def get_namespace_policies(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_namespace_policies(
            immute_domain=validated_params["cluster_domain"],
            namespace=validated_params["namespace"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("列出Pulsar集群所有在线broker地址。" "参数：cluster_domain（集群域名）")),
        request_slz=PulsarToolboxClusterInputSerializer,
        response_slz=ListBrokersOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def list_brokers(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_brokers(immute_domain=validated_params["cluster_domain"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Pulsar集群健康检查，执行broker自检并列出在线broker，返回集群整体健康状态。"
                "注意：不含BookKeeper层检查（需在bookie节点执行）。"
                "参数：cluster_domain（集群域名）"
            )
        ),
        request_slz=PulsarToolboxClusterInputSerializer,
        response_slz=ClusterHealthCheckOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_TOOLBOX],
        name_prefix="pulsar_toolbox",
    )
    def cluster_health_check(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = cluster_health_check(immute_domain=validated_params["cluster_domain"])
        return Response(result)
