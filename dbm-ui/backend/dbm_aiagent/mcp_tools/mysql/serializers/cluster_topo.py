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

from backend.db_meta.enums import InstanceRole, InstanceStatus, TenDBClusterSpiderRole
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_cluster_type_choices


class MySQLBaseInstanceSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices(), help_text=_("实例状态"))
    machine_type = serializers.CharField(help_text=_("实例机器类型"))


class MySQLStorageInstanceSerializer(MySQLBaseInstanceSerializer):
    is_stand_by = serializers.BooleanField(default=True, help_text=_("dbha 切换备选标志"))


class ClusterTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))


# TenDBSingle
class TenDBSingleTopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    storage = MySQLStorageInstanceSerializer(help_text=_("存储层实例信息"))


# TenDBHA
class TenDBHAStorageInstanceSerializer(MySQLStorageInstanceSerializer):
    backend_instance_role_choices = [
        (InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_MASTER.name),
        (InstanceRole.BACKEND_REPEATER.value, InstanceRole.BACKEND_REPEATER.name),
        (InstanceRole.BACKEND_SLAVE.value, InstanceRole.BACKEND_SLAVE.name),
    ]
    instance_role = serializers.ChoiceField(
        choices=backend_instance_role_choices, help_text=_("存储实例角色, backend instance role")
    )


class TenDBHATopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    proxy_instances = serializers.ListSerializer(
        child=MySQLBaseInstanceSerializer(), help_text=_("接入层实例列表, proxy instances list")
    )
    storage_instance = serializers.ListSerializer(
        child=TenDBHAStorageInstanceSerializer(), help_text=_("存储实例列表, backend instance list")
    )


# TenDBCluster
class TenDBClusterSpiderInstanceSerializer(MySQLBaseInstanceSerializer):
    spider_role = serializers.ChoiceField(
        choices=TenDBClusterSpiderRole.get_choices(), help_text=_("接入层角色, spider role")
    )


class TenDBClusterStorageInstanceSerializer(MySQLStorageInstanceSerializer):
    remote_instance_role_choices = [
        (InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_MASTER.name),
        (InstanceRole.REMOTE_REPEATER.value, InstanceRole.REMOTE_REPEATER.name),
        (InstanceRole.REMOTE_SLAVE.value, InstanceRole.REMOTE_SLAVE.name),
    ]
    instance_role = serializers.ChoiceField(
        choices=remote_instance_role_choices, help_text=_("存储实例角色, remote instance role")
    )


class TenDBClusterStorageReplicateSetSerializer(serializers.Serializer):
    shard_id = serializers.IntegerField(help_text=_("分片号"))
    instances = serializers.ListSerializer(child=TenDBClusterStorageInstanceSerializer(), help_text=_("同分片存储实例列表"))


class TenDBClusterTopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    spider_instances = serializers.ListSerializer(
        child=TenDBClusterSpiderInstanceSerializer(), help_text=_("接入层实例列表, spider list")
    )
    storage_replicate_sets = serializers.ListSerializer(
        child=TenDBClusterStorageReplicateSetSerializer(), help_text=_("按分片号组织的实例详情")
    )
