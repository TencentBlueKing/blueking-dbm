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

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER


class ListResourceSLZ(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    ip = serializers.CharField(required=False)
    domain = serializers.CharField(required=False)
    creator = serializers.CharField(required=False)
    version = serializers.CharField(required=False)
    region = serializers.CharField(required=False)
    cluster_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    exact_domain = serializers.CharField(help_text=_("精确域名查询"), required=False)


class ListMySQLResourceSLZ(ListResourceSLZ):
    db_module_id = serializers.IntegerField(required=False)


class ListMongoDBResourceSLZ(ListResourceSLZ):
    cluster_type = serializers.ChoiceField(required=False, choices=ClusterType.get_choices())
    domains = serializers.CharField(help_text=_("批量域名查询(逗号分割)"), required=False)


class ListSQLServerResourceSLZ(ListResourceSLZ):
    db_module_id = serializers.IntegerField(required=False)
    cluster_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)


class ClusterSLZ(serializers.ModelSerializer):
    cluster_name = serializers.CharField(source="name")
    cluster_alias = serializers.CharField(source="alias")

    class Meta:
        model = Cluster
        fields = ["id", "cluster_name", "cluster_type", "cluster_alias"]


class SearchResourceTreeSLZ(serializers.Serializer):
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices())


class InstanceAddressSerializer(serializers.Serializer):
    instance_address = serializers.CharField(help_text=_("实例地址(ip:port)"), required=False)
    ip = serializers.CharField(help_text=_("IP"), required=False)
    port = serializers.CharField(help_text=_("端口"), required=False)

    def to_internal_value(self, data):
        """获取根据address获取ip和port，优先考虑从address获取"""
        if "instance_address" not in data:
            return data

        instance_address = data["instance_address"]
        if IP_PORT_DIVIDER not in instance_address:
            data["ip"] = instance_address or data.get("ip", "")
            return data

        ip, port = instance_address.split(IP_PORT_DIVIDER, maxsplit=1)
        data["ip"] = ip
        try:
            data["port"] = int(port)
        except ValueError:
            # 非法端口，不进行查询过滤
            pass
        return data


class ListInstancesSerializer(InstanceAddressSerializer):
    domain = serializers.CharField(help_text=_("域名"), required=False)
    status = serializers.CharField(help_text=_("状态"), required=False)
    role = serializers.CharField(help_text=_("角色"), required=False)
    cluster_id = serializers.CharField(help_text=_("集群ID"), required=False)
    ip = serializers.CharField(required=False)


class MongoDBListInstancesSerializer(ListInstancesSerializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), required=False, choices=ClusterType.get_choices())
    exact_ip = serializers.CharField(help_text=_("精确IP查询"), required=False)


class RetrieveInstancesSerializer(InstanceAddressSerializer):
    """获取实例序列化器"""

    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    instance_address = serializers.CharField(help_text=_("实例地址(ip:port)"), required=True)


class ListNodesSLZ(serializers.Serializer):
    role = serializers.CharField(help_text=_("角色"))
    keyword = serializers.CharField(help_text=_("关键字过滤"), required=False, allow_blank=True)


class ListMachineSLZ(serializers.Serializer):
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"), required=False)
    ip = serializers.CharField(help_text=_("IP(多个IP过滤以逗号分隔)"), required=False)
    machine_type = serializers.ChoiceField(help_text=_("机器类型"), choices=MachineType.get_choices(), required=False)
    bk_os_name = serializers.CharField(help_text=_("os名字"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)
    bk_agent_id = serializers.CharField(help_text=_("agent id"), required=False)
    instance_role = serializers.CharField(help_text=_("机器部署的实例角色"), required=False)
    creator = serializers.CharField(help_text=_("创建者"), required=False)
