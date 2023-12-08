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

from backend.db_proxy.views import mock_data
from backend.db_proxy.views.serialiers import BaseProxyPassSerialier


class InstancesSerializer(BaseProxyPassSerialier):
    logical_city_ids = serializers.ListField(
        help_text=_("逻辑城市ID列表"), child=serializers.IntegerField(), allow_null=True, allow_empty=True, required=False
    )
    addresses = serializers.ListField(
        help_text=_("地址列表"), child=serializers.CharField(), allow_null=True, allow_empty=True, required=False
    )
    statuses = serializers.ListField(
        help_text=_("状态列表"), child=serializers.CharField(), allow_null=True, allow_empty=True, required=False
    )
    bk_cloud_id = serializers.IntegerField()


class InstancesResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.INSTANCE_DATA_RESPONSE}


class SwapRoleSerializer(BaseProxyPassSerialier):
    class SwapEleSerializer(serializers.Serializer):
        class SwapInstanceSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            port = serializers.IntegerField()

        instance1 = SwapInstanceSerializer()
        instance2 = SwapInstanceSerializer()

    payloads = serializers.ListSerializer(help_text=_("角色交换信息列表"), child=SwapEleSerializer())
    bk_cloud_id = serializers.IntegerField()


class TendisClusterSwapSerializer(BaseProxyPassSerialier):
    class PayloadSerializer(serializers.Serializer):
        class IpPortSerializer(serializers.Serializer):
            ip = serializers.CharField(help_text=_("实例IP"))
            port = serializers.CharField(help_text=_("实例Port"))

        master = IpPortSerializer()
        slave = IpPortSerializer()
        domain = serializers.CharField(help_text=_("domain信息"))

    payload = PayloadSerializer(help_text=_("tendis-swap的payload信息"))
    bk_cloud_id = serializers.IntegerField()


class UpdateStatusSerializer(BaseProxyPassSerialier):
    class UpdateStatusEleSerializer(serializers.Serializer):
        ip = serializers.IPAddressField()
        port = serializers.IntegerField(min_value=1025, max_value=65535)
        status = serializers.CharField()

    payloads = serializers.ListSerializer(
        help_text=_("更新状态的信息列表"), child=UpdateStatusEleSerializer(), allow_null=True, allow_empty=True
    )
    bk_cloud_id = serializers.IntegerField()


class EntryDetailSerializer(BaseProxyPassSerialier):
    domains = serializers.ListField(help_text=_("查询的domain列表"), child=serializers.CharField())


class MachinesClusterSerializer(BaseProxyPassSerialier):
    hosts = serializers.ListField(help_text=_("查询的Hosts列表"), child=serializers.CharField())


class ClusterDetailSerializer(BaseProxyPassSerialier):
    cluster_ids = serializers.ListField(help_text=_("查询的集群IDs"), child=serializers.CharField())


class BKCityNameSerializer(BaseProxyPassSerialier):
    logic_city_name = serializers.CharField(help_text=_("逻辑城市名称"))


class FakeTendbSingleCreateCluster(BaseProxyPassSerialier):
    storage_instance = serializers.CharField(help_text=_("实例"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    name = serializers.CharField(help_text=_("集群名"), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    db_module_id = serializers.IntegerField(help_text=_("模块ID"), required=False)


class FakeTendbHACreateCluster(BaseProxyPassSerialier):
    proxies = serializers.ListField(help_text=_("代理列表"))
    master_instance = serializers.CharField(help_text=_("master实例"))
    slave_instance = serializers.CharField(help_text=_("slave实例"))
    immute_domain = serializers.CharField(help_text=_("域名"))
    name = serializers.CharField(help_text=_("集群名"), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    db_module_id = serializers.IntegerField(help_text=_("模块ID"), required=False)
    slave_domain = serializers.CharField(help_text=_("从库域名"), required=False)


class FakeResetTendbHACluster(BaseProxyPassSerialier):
    proxies = serializers.ListField(help_text=_("proxy列表"), child=serializers.CharField())
    master_instance = serializers.CharField(help_text=_("master实例"))
    slave_instance = serializers.CharField(help_text=_("slave实例"))
    immute_domain = serializers.CharField(help_text=_("域名"))
    slave_domain = serializers.CharField(help_text=_("slave域名"), required=False)


class BizClusterSerializer(BaseProxyPassSerialier):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    immute_domains = serializers.ListField(help_text=_("域名列表"), child=serializers.CharField())


class ClusterInstanceSerializer(BaseProxyPassSerialier):
    immute_domain = serializers.CharField(help_text=_("域名列表"))


class InstanceDetailSLZ(BaseProxyPassSerialier):
    ip = serializers.CharField(help_text=_("ip"))
    port = serializers.IntegerField(help_text=_("port"))
    bk_cloud_id = serializers.IntegerField(help_text=_("bk_cloud_id"))


class TendbInstancesSerializer(BaseProxyPassSerialier):
    entry_name = serializers.CharField(help_text=_("访问入口"))
