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
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

# ============================================================
# 输入
# ============================================================

# Pulsar 租户/namespace 短名允许的字符集：字母数字及 - _ .
_NAME_SEGMENT = r"[-_.a-zA-Z0-9]+"

# 作为纵深防御的第二层：格式校验通不过的输入直接 400 拒绝，不会走到 shell 拼接那一步。
# 结构性防注入见 impl/pulsar_toolbox.py 里对这些字段统一做的 shlex.quote()。
tenant_validator = RegexValidator(regex=r"^{}$".format(_NAME_SEGMENT), message=_("租户名称格式不合法，仅允许字母、数字、-_."))
namespace_validator = RegexValidator(
    regex=r"^{0}/{0}$".format(_NAME_SEGMENT), message=_("namespace格式不合法，应为 tenant/namespace")
)
topic_validator = RegexValidator(
    regex=r"^(persistent|non-persistent)://{0}/{0}/{0}$".format(_NAME_SEGMENT),
    message=_("topic格式不合法，应为 persistent://tenant/namespace/topic"),
)


class PulsarToolboxClusterInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class ListNamespacesInputSerializer(PulsarToolboxClusterInputSerializer):
    tenant = serializers.CharField(help_text=_("租户名称，如 public"), validators=[tenant_validator])


class PulsarListTopicsInputSerializer(PulsarToolboxClusterInputSerializer):
    namespace = serializers.CharField(
        help_text=_("namespace名称，格式 tenant/namespace，如 public/default"), validators=[namespace_validator]
    )


class TopicInputSerializer(PulsarToolboxClusterInputSerializer):
    topic = serializers.CharField(
        help_text=_("topic完整名称，格式 persistent://tenant/namespace/topic，如 persistent://public/default/my-topic"),
        validators=[topic_validator],
    )


class NamespaceInputSerializer(PulsarToolboxClusterInputSerializer):
    namespace = serializers.CharField(
        help_text=_("namespace名称，格式 tenant/namespace，如 public/default"), validators=[namespace_validator]
    )


# ============================================================
# 输出
# ============================================================


class ListTenantsOutputSerializer(serializers.Serializer):
    tenants = serializers.ListField(child=serializers.CharField(), help_text=_("租户名称列表"))
    count = serializers.IntegerField(help_text=_("租户数量"))


class ListNamespacesOutputSerializer(serializers.Serializer):
    tenant = serializers.CharField(help_text=_("租户名称"))
    namespaces = serializers.ListField(child=serializers.CharField(), help_text=_("namespace名称列表"))
    count = serializers.IntegerField(help_text=_("namespace数量"))


class PulsarListTopicsOutputSerializer(serializers.Serializer):
    namespace = serializers.CharField(help_text=_("namespace名称"))
    topics = serializers.ListField(child=serializers.CharField(), help_text=_("topic名称列表"))
    count = serializers.IntegerField(help_text=_("topic数量"))


class PulsarDescribeTopicOutputSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic名称"))
    stats = serializers.DictField(
        help_text=_("topic统计信息，含 msgRateIn/msgRateOut(生产消费速率)、storageSize(存储大小)、subscriptions(各订阅积压)等")
    )


class TopicInternalStatsOutputSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic名称"))
    internal_stats = serializers.DictField(help_text=_("topic内部存储状态，含 ledgers(ledger分布)、entriesAddedCounter等"))


class ListSubscriptionsOutputSerializer(serializers.Serializer):
    topic = serializers.CharField(help_text=_("topic名称"))
    subscriptions = serializers.ListField(child=serializers.CharField(), help_text=_("订阅名称列表"))
    count = serializers.IntegerField(help_text=_("订阅数量"))


class NamespacePoliciesOutputSerializer(serializers.Serializer):
    namespace = serializers.CharField(help_text=_("namespace名称"))
    policies = serializers.DictField(help_text=_("namespace策略配置，含 retention_policies(保留策略)、persistence(持久化策略)、限流配置等"))


class ListBrokersOutputSerializer(serializers.Serializer):
    cluster_name = serializers.CharField(help_text=_("Pulsar集群名"))
    brokers = serializers.ListField(child=serializers.CharField(), help_text=_("在线broker地址列表(host:port)"))
    count = serializers.IntegerField(help_text=_("在线broker数量"))


class PulsarClusterHealthCheckOutputSerializer(serializers.Serializer):
    cluster_name = serializers.CharField(help_text=_("Pulsar集群名"))
    healthcheck_ok = serializers.BooleanField(help_text=_("broker自检是否通过"))
    healthcheck_output = serializers.CharField(help_text=_("broker自检原始输出"))
    brokers = serializers.ListField(child=serializers.CharField(), help_text=_("在线broker地址列表"))
    broker_count = serializers.IntegerField(help_text=_("在线broker数量"))
    healthy = serializers.BooleanField(help_text=_("集群整体是否健康"))
