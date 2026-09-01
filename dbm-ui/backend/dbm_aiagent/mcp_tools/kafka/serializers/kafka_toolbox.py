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
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

# ============================================================
# 公共基础序列化器
# ============================================================


class KafkaToolboxBaseInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名(immute_domain)"))


# ============================================================
# 只读工具 - 输入序列化器
# ============================================================


class KafkaListTopicsInputSerializer(KafkaToolboxBaseInputSerializer):
    pass


class ClusterHealthCheckInputSerializer(KafkaToolboxBaseInputSerializer):
    pass


class ConsumeTopicSampleInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    max_messages = serializers.IntegerField(
        help_text=_("最多采样消息条数，默认10，上限20"),
        required=False,
        default=10,
    )
    from_beginning = serializers.BooleanField(
        help_text=_("是否从头开始消费。True=从最早消息开始，False=只等待新消息"),
        required=False,
        default=True,
    )
    timeout_ms = serializers.IntegerField(
        help_text=_("等待超时毫秒数，默认10000(10秒)"),
        required=False,
        default=10000,
    )

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_max_messages(self, value):
        if value < 1:
            raise serializers.ValidationError(_("max_messages 必须大于0"))
        if value > 20:
            raise serializers.ValidationError(_("max_messages 不能超过20，避免输出过大"))
        return value

    def validate_timeout_ms(self, value):
        if value < 1000:
            raise serializers.ValidationError(_("timeout_ms 不能小于1000"))
        if value > 30000:
            raise serializers.ValidationError(_("timeout_ms 不能超过30000"))
        return value


class DescribeTopicInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value


class ListConsumerGroupsInputSerializer(KafkaToolboxBaseInputSerializer):
    pass


class DescribeConsumerGroupInputSerializer(KafkaToolboxBaseInputSerializer):
    group = serializers.CharField(help_text=_("消费组名称"))

    def validate_group(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("消费组名称只能包含字母、数字、点、下划线和连字符"))
        return value


class GetTopicConfigInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value


class GetBrokerConfigInputSerializer(KafkaToolboxBaseInputSerializer):
    broker_id = serializers.IntegerField(help_text=_("broker ID"))


class AlterTopicConfigInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    config_key = serializers.CharField(help_text=_("配置项名称，如 retention.ms, cleanup.policy, max.message.bytes 等"))
    config_value = serializers.CharField(help_text=_("配置项的值"))

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_config_key(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("配置项名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_config_value(self, value):
        if not re.match(r"^[a-zA-Z0-9._:/-]+$", value):
            raise serializers.ValidationError(_("配置项值包含非法字符"))
        return value


class AlterTopicPartitionsInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    partitions = serializers.IntegerField(help_text=_("目标分区数，只能增加不能减少"))

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_partitions(self, value):
        if value < 1:
            raise serializers.ValidationError(_("分区数必须大于0"))
        if value > 10000:
            raise serializers.ValidationError(_("分区数不能超过10000"))
        return value


class DeleteTopicConfigInputSerializer(KafkaToolboxBaseInputSerializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    config_key = serializers.CharField(help_text=_("要重置为默认值的配置项名称"))

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_config_key(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("配置项名称只能包含字母、数字、点、下划线和连字符"))
        return value


class ResetConsumerGroupOffsetInputSerializer(KafkaToolboxBaseInputSerializer):
    group = serializers.CharField(help_text=_("消费组名称"))
    topic = serializers.CharField(help_text=_("topic 名称"))
    strategy = serializers.ChoiceField(
        choices=[
            ("to-earliest", _("重置到最早")),
            ("to-latest", _("重置到最新")),
            ("to-offset", _("重置到指定offset")),
            ("to-datetime", _("重置到指定时间点")),
        ],
        help_text=_("重置策略: to-earliest, to-latest, to-offset, to-datetime"),
    )
    strategy_value = serializers.CharField(
        help_text=_("策略参数值。to-offset时为offset数值，to-datetime时为'YYYY-MM-DDTHH:mm:ss.000'格式时间"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
    )

    def validate_group(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("消费组名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_topic(self, value):
        if not re.match(r"^[a-zA-Z0-9._-]+$", value):
            raise serializers.ValidationError(_("topic 名称只能包含字母、数字、点、下划线和连字符"))
        return value

    def validate_strategy_value(self, value):
        if not re.match(r"^[a-zA-Z0-9._:T-]*$", value):
            raise serializers.ValidationError(_("strategy_value 包含非法字符"))
        return value

    def validate(self, attrs):
        strategy = attrs.get("strategy")
        strategy_value = attrs.get("strategy_value", "")
        if strategy in ("to-offset", "to-datetime") and not strategy_value:
            raise serializers.ValidationError(_("使用 {} 策略时 strategy_value 必填").format(strategy))
        if strategy == "to-offset":
            try:
                int(strategy_value)
            except ValueError:
                raise serializers.ValidationError(_("to-offset 策略的 strategy_value 必须是整数"))
        return attrs


# ============================================================
# 只读工具 - 输出序列化器
# ============================================================


class KafkaListTopicsOutputSerializer(serializers.Serializer):
    topics = serializers.ListField(child=serializers.CharField(), help_text=_("topic 列表"))
    count = serializers.IntegerField(help_text=_("topic 数量"))


class PartitionInfoSerializer(serializers.Serializer):
    partition = serializers.IntegerField(help_text=_("分区编号"), required=False)
    leader = serializers.IntegerField(help_text=_("leader broker ID"), required=False)
    replicas = serializers.ListField(child=serializers.IntegerField(), help_text=_("副本列表"), required=False)
    isr = serializers.ListField(child=serializers.IntegerField(), help_text=_("ISR 列表"), required=False)


class KafkaDescribeTopicOutputSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    partition_count = serializers.IntegerField(help_text=_("分区数"))
    replication_factor = serializers.IntegerField(help_text=_("副本因子"))
    configs = serializers.DictField(child=serializers.CharField(), help_text=_("配置项"))
    partitions = PartitionInfoSerializer(many=True, help_text=_("分区详情列表"))


class ListConsumerGroupsOutputSerializer(serializers.Serializer):
    groups = serializers.ListField(child=serializers.CharField(), help_text=_("消费组列表"))
    count = serializers.IntegerField(help_text=_("消费组数量"))


class ConsumerGroupMemberSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic 名称"), required=False)
    partition = serializers.IntegerField(help_text=_("分区编号"), required=False)
    current_offset = serializers.IntegerField(help_text=_("当前 offset"), required=False)
    log_end_offset = serializers.IntegerField(help_text=_("日志末尾 offset"), required=False)
    lag = serializers.IntegerField(help_text=_("消费延迟"), required=False)
    consumer_id = serializers.CharField(help_text=_("消费者 ID"), required=False)
    host = serializers.CharField(help_text=_("消费者主机"), required=False)
    client_id = serializers.CharField(help_text=_("客户端 ID"), required=False)


class DescribeConsumerGroupOutputSerializer(serializers.Serializer):
    group = serializers.CharField(help_text=_("消费组名称"))
    state = serializers.CharField(help_text=_("消费组状态"), required=False)
    members = ConsumerGroupMemberSerializer(many=True, help_text=_("消费组成员列表"))


class ConfigOutputSerializer(serializers.Serializer):
    entity_type = serializers.CharField(help_text=_("实体类型 (topic/broker)"))
    entity_name = serializers.CharField(help_text=_("实体名称"))
    configs = serializers.DictField(child=serializers.CharField(), help_text=_("配置项"))


class BrokerInfoSerializer(serializers.Serializer):
    host = serializers.CharField(help_text=_("broker 主机名/IP"))
    port = serializers.IntegerField(help_text=_("broker 端口"))
    id = serializers.IntegerField(help_text=_("broker ID"))
    rack = serializers.CharField(help_text=_("rack 信息"), required=False, allow_null=True)


class ProblemPartitionSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic 名称"), required=False)
    partition = serializers.IntegerField(help_text=_("分区编号"), required=False)
    leader = serializers.IntegerField(help_text=_("leader broker ID"), required=False)
    replicas = serializers.ListField(child=serializers.IntegerField(), help_text=_("副本列表"), required=False)
    isr = serializers.ListField(child=serializers.IntegerField(), help_text=_("ISR 列表"), required=False)


class KafkaClusterHealthCheckOutputSerializer(serializers.Serializer):
    brokers = BrokerInfoSerializer(many=True, help_text=_("在线 broker 列表"))
    broker_count = serializers.IntegerField(help_text=_("在线 broker 数量"))
    under_replicated_partitions = ProblemPartitionSerializer(many=True, help_text=_("副本不足的分区列表"))
    under_replicated_count = serializers.IntegerField(help_text=_("副本不足分区数量"))
    unavailable_partitions = ProblemPartitionSerializer(many=True, help_text=_("不可用的分区列表"))
    unavailable_count = serializers.IntegerField(help_text=_("不可用分区数量"))
    healthy = serializers.BooleanField(help_text=_("集群是否健康（无副本不足且无不可用分区）"))


class ConsumeTopicSampleOutputSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic 名称"))
    messages = serializers.ListField(child=serializers.CharField(), help_text=_("采样的消息列表"))
    count = serializers.IntegerField(help_text=_("实际采样到的消息数量"))


class ResetConsumerGroupOffsetOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text=_("操作是否成功"))
    group = serializers.CharField(help_text=_("消费组名称"))
    topic = serializers.CharField(help_text=_("topic 名称"))
    strategy = serializers.CharField(help_text=_("使用的重置策略"))
    output = serializers.CharField(help_text=_("CLI 原始输出"))


# ============================================================
# 写操作 - 输出序列化器
# ============================================================


class AlterTopicConfigOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text=_("操作是否成功"))
    topic = serializers.CharField(help_text=_("topic 名称"))
    config_key = serializers.CharField(help_text=_("配置项名称"))
    config_value = serializers.CharField(help_text=_("配置项值"))
    output = serializers.CharField(help_text=_("CLI 原始输出"))


class AlterTopicPartitionsOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text=_("操作是否成功"))
    topic = serializers.CharField(help_text=_("topic 名称"))
    partitions = serializers.IntegerField(help_text=_("目标分区数"))
    output = serializers.CharField(help_text=_("CLI 原始输出"))


class DeleteTopicConfigOutputSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text=_("操作是否成功"))
    topic = serializers.CharField(help_text=_("topic 名称"))
    config_key = serializers.CharField(help_text=_("配置项名称"))
    output = serializers.CharField(help_text=_("CLI 原始输出"))
