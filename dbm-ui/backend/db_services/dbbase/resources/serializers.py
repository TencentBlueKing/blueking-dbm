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

from backend.db_meta.enums import ClusterStatus, ClusterType, InstanceStatus, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.flow.consts import SqlserverSyncMode


class ListResourceSLZ(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    ip = serializers.CharField(required=False)
    instance = serializers.CharField(required=False)
    domain = serializers.CharField(required=False)
    creator = serializers.CharField(required=False)
    major_version = serializers.CharField(required=False)
    region = serializers.CharField(required=False)
    cluster_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    exact_domain = serializers.CharField(help_text=_("精确域名查询"), required=False)
    ordering = serializers.CharField(required=False, help_text=_("排序字段,非必填"))
    status = serializers.CharField(required=False, help_text=_("状态"))
    db_module_id = serializers.CharField(required=False, help_text=_("所属DB模块"))
    bk_cloud_id = serializers.CharField(required=False, help_text=_("管控区域"))
    cluster_type = serializers.CharField(required=False, help_text=_("集群类型"))


class ListMySQLResourceSLZ(ListResourceSLZ):
    master_domain = serializers.CharField(required=False)
    slave_domain = serializers.CharField(required=False)


class ListTendbClusterResourceSLZ(ListMySQLResourceSLZ):
    spider_slave_exist = serializers.BooleanField(required=False)


class ListRedisResourceSLZ(ListResourceSLZ):
    pass


class ListSQLServerResourceSLZ(ListResourceSLZ):
    sys_mode = serializers.ChoiceField(help_text=_("模块类型"), choices=SqlserverSyncMode.get_choices(), required=False)


class ListMongoDBResourceSLZ(ListResourceSLZ):
    domains = serializers.CharField(help_text=_("批量域名查询(逗号分割)"), required=False)


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

        all_ports_valid = True

        """获取根据address获取ip和port，优先考虑从address获取"""
        if "instance_address" not in data:
            return data

        instance_address = data["instance_address"]
        # 用于分隔IP地址和端口号的部分
        parts = instance_address.split(",")
        for part in parts:
            if IP_PORT_DIVIDER in part:
                # 存在端口号,进行验证
                ip, port = part.split(IP_PORT_DIVIDER, maxsplit=1)
                if not port.isdigit():
                    # 非法端口
                    all_ports_valid = False
                    break

        if not all_ports_valid:
            pass
        # 如果所有端口都有效，则将instance_address保存到data字典
        data.update({"instance": instance_address})
        return data


class ListInstancesSerializer(InstanceAddressSerializer):
    domain = serializers.CharField(help_text=_("域名"), required=False)
    status = serializers.CharField(help_text=_("状态"), required=False)
    role = serializers.CharField(help_text=_("角色"), required=False)
    cluster_id = serializers.CharField(help_text=_("集群ID"), required=False)
    cluster_type = serializers.CharField(required=False, help_text=_("集群类型"))
    ip = serializers.CharField(required=False)


class SqlserverListInstanceSerializer(ListInstancesSerializer):
    db_module_id = serializers.CharField(required=False, help_text=_("所属DB模块"))


class MongoDBListInstancesSerializer(ListInstancesSerializer):
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
    cluster_ids = serializers.CharField(help_text=_("集群ID(多个过滤以逗号分隔)"), required=False)
    cluster_status = serializers.ChoiceField(help_text=_("集群状态"), choices=ClusterStatus.get_choices(), required=False)
    cluster_type = serializers.CharField(help_text=_("集群类型"), required=False)
    bk_city_name = serializers.CharField(help_text=_("城市名(多个过滤以逗号分隔)"), required=False)
    machine_type = serializers.ChoiceField(help_text=_("机器类型"), choices=MachineType.get_choices(), required=False)
    bk_os_name = serializers.CharField(help_text=_("os名字"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)
    bk_agent_id = serializers.CharField(help_text=_("agent id"), required=False)
    instance_role = serializers.CharField(help_text=_("机器部署的实例角色"), required=False)
    instance_status = serializers.ChoiceField(
        help_text=_("集群状态"), choices=InstanceStatus.get_choices(), required=False
    )
    creator = serializers.CharField(help_text=_("创建者"), required=False)


class ListRedisMachineResourceSLZ(ListMachineSLZ):
    add_role_count = serializers.BooleanField(required=False)


class ListTendbClusterMachineResourceSLZ(ListMachineSLZ):
    spider_role = serializers.ChoiceField(
        help_text=_("spider角色"), choices=TenDBClusterSpiderRole.get_choices(), required=False
    )
