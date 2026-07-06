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


class MySQLClusterRuntimeVariablesInputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(
        help_text=_("集群 ID，与 cluster_domain 二选一"),
        required=False,
        allow_null=True,
    )
    cluster_domain = serializers.CharField(
        help_text=_("集群域名，与 cluster_id 二选一"),
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs):
        cluster_id = attrs.get("cluster_id")
        cluster_domain = (attrs.get("cluster_domain") or "").strip()
        if cluster_id is None and not cluster_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 必须提供其一"))
        if cluster_id is not None and cluster_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 只能提供其一"))
        if cluster_domain:
            attrs["cluster_domain"] = cluster_domain
        return attrs


class InstanceVariablesSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    instance_role = serializers.CharField(help_text=_("实例角色"), default="", allow_blank=True)
    machine_type = serializers.CharField(help_text=_("实例机器类型"))
    version = serializers.CharField(help_text=_("版本号"), default="", allow_blank=True)
    is_stand_by = serializers.BooleanField(
        help_text=_("是否为 standby（TenDBHA 多 slave 时的备选从库标志）；Spider 实例无此语义时可缺省"),
        required=False,
        default=False,
    )
    datadir = serializers.CharField(
        help_text=_("MySQL 变量 datadir 原始值(完整路径)"),
        default="",
        allow_blank=True,
    )
    data_dir_mount = serializers.CharField(
        help_text=_("数据盘挂载点前缀(/data、/data1 等), 与 DBM 路径约定一致; 无法从路径解析时为空"),
        default="",
        allow_blank=True,
    )
    variables = serializers.DictField(child=serializers.CharField(), help_text=_("运行时核心参数(已过滤目录/路径类)"))


class ShardVariablesSerializer(serializers.Serializer):
    master = InstanceVariablesSerializer(help_text=_("分片主实例配置"))
    slave = InstanceVariablesSerializer(help_text=_("分片从实例配置"), required=False)


class MySQLClusterRuntimeVariablesOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    master = InstanceVariablesSerializer(help_text=_("主实例配置, TenDBSingle/TenDBHA 有效"), required=False)
    slaves = serializers.ListField(
        child=InstanceVariablesSerializer(),
        help_text=_("从实例配置列表, TenDBSingle/TenDBHA 有效"),
        required=False,
        default=list,
    )
    spiders = serializers.ListField(
        child=InstanceVariablesSerializer(),
        help_text=_("Spider 接入层配置列表, TenDBCluster 有效"),
        required=False,
        default=list,
    )
    shards = serializers.DictField(
        child=ShardVariablesSerializer(),
        help_text=_("以 shard_id 为 key 的分片配置, TenDBCluster 有效"),
        required=False,
        default=dict,
    )
