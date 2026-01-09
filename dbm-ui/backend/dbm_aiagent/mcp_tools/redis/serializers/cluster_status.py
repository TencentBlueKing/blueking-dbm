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

# ==================== 输入序列化器 ====================


class RedisClusterInputSerializer(serializers.Serializer):
    """Redis集群输入序列化器"""

    immute_domain = serializers.CharField(help_text=_("集群域名"))


# ==================== 输出序列化器 ====================


class RedisSlaveNodeSerializer(serializers.Serializer):
    """从节点信息"""

    ip = serializers.CharField(help_text=_("从节点IP"))
    port = serializers.IntegerField(help_text=_("从节点端口"))
    keys = serializers.IntegerField(help_text=_("键数量"))
    memory_human = serializers.CharField(help_text=_("内存使用（人类可读）"))
    qps = serializers.IntegerField(help_text=_("每秒查询数"))
    status = serializers.CharField(help_text=_("状态"))
    replication_lag = serializers.IntegerField(help_text=_("复制延迟（字节）"), required=False)


class RedisMasterNodeSerializer(serializers.Serializer):
    """主节点信息"""

    ip = serializers.CharField(help_text=_("主节点IP"))
    port = serializers.IntegerField(help_text=_("主节点端口"))
    keys = serializers.IntegerField(help_text=_("键数量"))
    memory_human = serializers.CharField(help_text=_("内存使用（人类可读）"))
    qps = serializers.IntegerField(help_text=_("每秒查询数"))
    status = serializers.CharField(help_text=_("状态"))
    connected_slaves = serializers.IntegerField(help_text=_("已连接从节点数"))
    total_slaves = serializers.IntegerField(help_text=_("总从节点数"))
    slaves = RedisSlaveNodeSerializer(many=True, help_text=_("从节点列表"))


class RedisClusterTopologyResponseSerializer(serializers.Serializer):
    """Redis集群拓扑响应"""

    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    total_masters = serializers.IntegerField(help_text=_("主节点总数"))
    total_slaves = serializers.IntegerField(help_text=_("从节点总数"))
    total_keys = serializers.IntegerField(help_text=_("总键数量"))
    total_qps = serializers.IntegerField(help_text=_("集群总QPS"))
    masters = RedisMasterNodeSerializer(many=True, help_text=_("主节点列表"))


class RedisClusterTopologyTextSerializer(serializers.Serializer):
    """Redis集群拓扑文本格式响应"""

    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    topology_text = serializers.CharField(help_text=_("拓扑文本（格式化显示）"))
    summary = serializers.DictField(help_text=_("汇总信息"))
