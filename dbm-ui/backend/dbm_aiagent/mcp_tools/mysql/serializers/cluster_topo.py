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


class MySQLClusterTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class MySQLBaseInstanceSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    status = serializers.CharField(help_text=_("实例状态"))
    machine_type = serializers.CharField(help_text=_("实例机器类型"))


#
#
class MySQLStorageInstanceSerializer(MySQLBaseInstanceSerializer):
    instance_role = serializers.CharField(help_text=_("实例角色"))
    instance_inner_role = serializers.CharField(help_text=_("实例内部角色"))
    is_stand_by = serializers.BooleanField(default=True, help_text=_("dbha 切换备选标志"))


class MySQLStorageInstanceReplicateSetSerializer(serializers.Serializer):
    shard_id = serializers.IntegerField(help_text=_("分片号"), default=None, required=False)
    master_instance = MySQLStorageInstanceSerializer(help_text=_("主实例"))
    slave_instances = serializers.ListSerializer(
        child=MySQLStorageInstanceSerializer(), help_text=_("从实例列表"), default=[], required=False
    )


class MySQLClusterTopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    proxy_instances = serializers.ListSerializer(child=MySQLBaseInstanceSerializer(), help_text=_("接入层实例列表"))
    storage_instance_replicate_sets = serializers.ListSerializer(
        child=MySQLStorageInstanceReplicateSetSerializer(), help_text=_("按分片号组织的实例详情")
    )
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    region = serializers.CharField(help_text=_("地域"))
    tolerance_level = serializers.IntegerField(help_text=_("容灾级别"))
    time_zone = serializers.CharField(help_text=_("时区"))
