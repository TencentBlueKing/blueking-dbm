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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_runtime_variables import (
    MySQLClusterRuntimeVariablesInputSerializer,
)


class VariableMismatchSerializer(serializers.Serializer):
    variable_name = serializers.CharField(help_text=_("变量名"))
    left_value = serializers.CharField(help_text=_("左侧实例取值（HA/分片为 master；Spider 为字典序较小地址）"), allow_blank=True)
    right_value = serializers.CharField(help_text=_("右侧实例取值（HA/分片为 slave；Spider 为字典序较大地址）"), allow_blank=True)
    severity = serializers.CharField(help_text=_("严重度 high|warn"))


class ReplicationPairSerializer(serializers.Serializer):
    scope = serializers.CharField(help_text=_("master_slave | replica_group"))
    master = serializers.CharField(help_text=_("主实例地址"), required=False, allow_blank=True, allow_null=True)
    slave = serializers.CharField(help_text=_("从实例地址"), required=False, allow_blank=True, allow_null=True)
    affected_slaves = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("replica_group 时受影响的从实例列表"),
        required=False,
        default=list,
    )
    mismatches = serializers.ListField(child=VariableMismatchSerializer(), help_text=_("差异参数列表"))


class SpiderVersionItemSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("Spider 地址"))
    instance_role = serializers.CharField(help_text=_("Spider 角色"), allow_blank=True)
    version = serializers.CharField(help_text=_("版本号"), allow_blank=True)


class SpiderVersionDiffSerializer(serializers.Serializer):
    is_consistent = serializers.BooleanField(help_text=_("各 Spider 版本是否一致"))
    versions = serializers.ListField(child=serializers.CharField(), help_text=_("去重后的版本列表"))


class SpiderPeerPairSerializer(serializers.Serializer):
    scope = serializers.CharField(help_text=_("spider_peer"))
    peer_a = serializers.CharField(help_text=_("对等 Spider A（字典序较小）"))
    peer_b = serializers.CharField(help_text=_("对等 Spider B（字典序较大）"))
    mismatches = serializers.ListField(child=VariableMismatchSerializer(), help_text=_("差异参数列表"))


class ShardPairExampleSerializer(serializers.Serializer):
    shard_id = serializers.CharField(help_text=_("示例分片 ID"), allow_null=True)
    master = serializers.CharField(help_text=_("示例主实例"), allow_null=True, allow_blank=True)
    slave = serializers.CharField(help_text=_("示例从实例"), allow_null=True, allow_blank=True)


class ShardPairSerializer(serializers.Serializer):
    scope = serializers.CharField(help_text=_("shard | shard_group"))
    shard_id = serializers.CharField(help_text=_("分片 ID"), required=False, allow_null=True)
    affected_shards = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("shard_group 时受影响的分片 ID 列表"),
        required=False,
        default=list,
    )
    master = serializers.CharField(help_text=_("主实例地址"), required=False, allow_blank=True, allow_null=True)
    slave = serializers.CharField(help_text=_("从实例地址"), required=False, allow_blank=True, allow_null=True)
    pairs_example = ShardPairExampleSerializer(help_text=_("shard_group 示例对"), required=False)
    mismatches = serializers.ListField(child=VariableMismatchSerializer(), help_text=_("差异参数列表"))


class TenDBHAMasterSlaveVariableDiffInputSerializer(MySQLClusterRuntimeVariablesInputSerializer):
    """入参与 cluster_runtime_variables 相同：cluster_id / cluster_domain 二选一。"""


class TenDBHAMasterSlaveVariableDiffOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"), allow_blank=True)
    replication_pairs = serializers.ListField(
        child=ReplicationPairSerializer(),
        help_text=_("主从参数差异列表；无差异为空"),
    )


class TenDBClusterVariableDiffInputSerializer(MySQLClusterRuntimeVariablesInputSerializer):
    """入参与 cluster_runtime_variables 相同：cluster_id / cluster_domain 二选一。"""


class TenDBClusterVariableDiffOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"), allow_blank=True)
    spider_versions = serializers.ListField(
        child=SpiderVersionItemSerializer(),
        help_text=_("各 Spider 版本信息"),
    )
    spider_version_diff = SpiderVersionDiffSerializer(help_text=_("Spider 版本一致性摘要"))
    spider_pairs = serializers.ListField(
        child=SpiderPeerPairSerializer(),
        help_text=_("Spider 对等参数差异；无差异为空"),
    )
    shard_pairs = serializers.ListField(
        child=ShardPairSerializer(),
        help_text=_("分片内主从参数差异；无差异为空"),
    )
