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
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_toolbox import (
    alter_topic_config,
    alter_topic_partitions,
    cluster_health_check,
    consume_topic_sample,
    delete_topic_config,
    describe_consumer_group,
    describe_topic,
    get_broker_config,
    get_topic_config,
    list_consumer_groups,
    list_topics,
    reset_consumer_group_offset,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_toolbox import (
    AlterTopicConfigInputSerializer,
    AlterTopicConfigOutputSerializer,
    AlterTopicPartitionsInputSerializer,
    AlterTopicPartitionsOutputSerializer,
    ClusterHealthCheckInputSerializer,
    ConfigOutputSerializer,
    ConsumeTopicSampleInputSerializer,
    ConsumeTopicSampleOutputSerializer,
    DeleteTopicConfigInputSerializer,
    DeleteTopicConfigOutputSerializer,
    DescribeConsumerGroupInputSerializer,
    DescribeConsumerGroupOutputSerializer,
    DescribeTopicInputSerializer,
    GetBrokerConfigInputSerializer,
    GetTopicConfigInputSerializer,
    KafkaClusterHealthCheckOutputSerializer,
    KafkaDescribeTopicOutputSerializer,
    KafkaListTopicsInputSerializer,
    KafkaListTopicsOutputSerializer,
    ListConsumerGroupsInputSerializer,
    ListConsumerGroupsOutputSerializer,
    ResetConsumerGroupOffsetInputSerializer,
    ResetConsumerGroupOffsetOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Kafka 工具箱 MCP - 在 Kafka 集群 broker 上远程执行 Kafka CLI 命令
- 只读：list_topics, describe_topic, list_consumer_groups, describe_consumer_group, get_topic_config, get_broker_config
- 写操作：alter_topic_config, delete_topic_config
"""


class KafkaToolboxMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("列出Kafka集群所有topic。" "返回集群中所有topic的名称列表和数量。" "参数：cluster_domain（集群域名）")),
        request_slz=KafkaListTopicsInputSerializer,
        response_slz=KafkaListTopicsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def list_topics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_topics(immute_domain=validated_params["cluster_domain"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("查看Kafka topic详细信息，包括分区数、副本因子、ISR列表、配置等。" "参数：cluster_domain（集群域名），topic（topic名称）")),
        request_slz=DescribeTopicInputSerializer,
        response_slz=KafkaDescribeTopicOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def describe_topic(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = describe_topic(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("列出Kafka集群所有消费组。" "返回集群中所有消费组的名称列表和数量。" "参数：cluster_domain（集群域名）")),
        request_slz=ListConsumerGroupsInputSerializer,
        response_slz=ListConsumerGroupsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def list_consumer_groups(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = list_consumer_groups(immute_domain=validated_params["cluster_domain"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("查看Kafka消费组详细信息，包括各分区的offset、lag、消费者分配情况。" "参数：cluster_domain（集群域名），group（消费组名称）")),
        request_slz=DescribeConsumerGroupInputSerializer,
        response_slz=DescribeConsumerGroupOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def describe_consumer_group(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = describe_consumer_group(
            immute_domain=validated_params["cluster_domain"],
            group=validated_params["group"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("查看Kafka topic配置覆盖项，返回通过kafka-configs设置的非默认配置。" "参数：cluster_domain（集群域名），topic（topic名称）")),
        request_slz=GetTopicConfigInputSerializer,
        response_slz=ConfigOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def get_topic_config(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_topic_config(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _("查看Kafka broker配置覆盖项，返回通过kafka-configs设置的非默认配置。" "参数：cluster_domain（集群域名），broker_id（broker ID）")
        ),
        request_slz=GetBrokerConfigInputSerializer,
        response_slz=ConfigOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def get_broker_config(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_broker_config(
            immute_domain=validated_params["cluster_domain"],
            broker_id=validated_params["broker_id"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "修改Kafka topic配置项（如retention.ms、cleanup.policy、max.message.bytes等）。"
                "参数：cluster_domain（集群域名），topic（topic名称），config_key（配置项名称），config_value（配置值）"
            )
        ),
        request_slz=AlterTopicConfigInputSerializer,
        response_slz=AlterTopicConfigOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def alter_topic_config(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = alter_topic_config(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
            config_key=validated_params["config_key"],
            config_value=validated_params["config_value"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _("修改Kafka topic分区数（只能增加不能减少，不可逆操作）。" "参数：cluster_domain（集群域名），topic（topic名称），partitions（目标分区数，必须大于当前分区数）")
        ),
        request_slz=AlterTopicPartitionsInputSerializer,
        response_slz=AlterTopicPartitionsOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def alter_topic_partitions(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = alter_topic_partitions(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
            partitions=validated_params["partitions"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "重置Kafka topic配置项为默认值（删除通过kafka-configs设置的覆盖配置）。"
                "参数：cluster_domain（集群域名），topic（topic名称），config_key（要重置的配置项名称）"
            )
        ),
        request_slz=DeleteTopicConfigInputSerializer,
        response_slz=DeleteTopicConfigOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def delete_topic_config(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = delete_topic_config(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
            config_key=validated_params["config_key"],
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "重置Kafka消费组offset。支持4种策略："
                "to-earliest（重置到最早），to-latest（重置到最新），"
                "to-offset（重置到指定offset，需提供strategy_value为数值），"
                "to-datetime（重置到指定时间点，需提供strategy_value为'YYYY-MM-DDTHH:mm:ss.000'格式）。"
                "注意：消费组必须处于非活跃状态（所有消费者已停止）才能重置。"
            )
        ),
        request_slz=ResetConsumerGroupOffsetInputSerializer,
        response_slz=ResetConsumerGroupOffsetOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def reset_consumer_group_offset(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = reset_consumer_group_offset(
            immute_domain=validated_params["cluster_domain"],
            group=validated_params["group"],
            topic=validated_params["topic"],
            strategy=validated_params["strategy"],
            strategy_value=validated_params.get("strategy_value", ""),
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("Kafka集群健康检查。返回在线broker列表、副本不足分区、不可用分区，以及整体健康状态。" "参数：cluster_domain（集群域名）")),
        request_slz=ClusterHealthCheckInputSerializer,
        response_slz=KafkaClusterHealthCheckOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def cluster_health_check(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = cluster_health_check(immute_domain=validated_params["cluster_domain"])
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "采样Kafka topic消息，用于确认topic中是否有数据以及数据格式。"
                "默认从头消费最多10条消息，超时10秒。"
                "参数：cluster_domain（集群域名），topic（topic名称），"
                "max_messages（最多采样条数，默认10，上限20），"
                "from_beginning（是否从头消费，默认true），"
                "timeout_ms（超时毫秒数，默认10000）"
            )
        ),
        request_slz=ConsumeTopicSampleInputSerializer,
        response_slz=ConsumeTopicSampleOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_TOOLBOX],
        name_prefix="kafka_toolbox",
    )
    def consume_topic_sample(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = consume_topic_sample(
            immute_domain=validated_params["cluster_domain"],
            topic=validated_params["topic"],
            max_messages=validated_params.get("max_messages", 10),
            from_beginning=validated_params.get("from_beginning", True),
            timeout_ms=validated_params.get("timeout_ms", 10000),
        )
        return Response(result)
