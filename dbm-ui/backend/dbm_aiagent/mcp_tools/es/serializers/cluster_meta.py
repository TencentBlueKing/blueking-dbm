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


class EsBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class EsBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名"))


class EsBizDetailSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class EsClusterInputSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))


class EsClusterOutputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    es_version = serializers.CharField(help_text=_("ES版本"))
    region = serializers.CharField(help_text=_("地域"))
    master_count = serializers.IntegerField(help_text=_("Master节点数"))
    hot_count = serializers.IntegerField(help_text=_("Hot节点数"))
    cold_count = serializers.IntegerField(help_text=_("Cold节点数"))
    client_count = serializers.IntegerField(help_text=_("Client节点数"))


class EsClusterEntrySerializer(serializers.Serializer):
    entry_type = serializers.CharField(help_text=_("入口类型"))
    entry_addr = serializers.CharField(help_text=_("入口地址"))


class EsNodeSpecSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    cpu = serializers.DictField(help_text=_("CPU规格"))
    memory = serializers.DictField(help_text=_("内存规格"))
    storage_spec = serializers.ListField(help_text=_("存储规格"))


class EsNodeSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("节点IP"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    port = serializers.IntegerField(help_text=_("端口"))
    instance_id = serializers.IntegerField(help_text=_("实例ID"))
    status = serializers.CharField(help_text=_("实例状态"))
    device_class = serializers.CharField(help_text=_("设备类型"))
    spec = EsNodeSpecSerializer(help_text=_("规格信息"), required=False)


class EsSpecDetailSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    cpu = serializers.DictField(help_text=_("CPU规格"))
    memory = serializers.DictField(help_text=_("内存规格"))
    storage_spec = serializers.ListField(help_text=_("存储规格"))
    device_class = serializers.CharField(help_text=_("设备类型"))
    desc = serializers.CharField(help_text=_("规格描述"))


class EsRoleStatsSerializer(serializers.Serializer):
    role = serializers.CharField(help_text=_("角色标识"))
    node_count = serializers.IntegerField(help_text=_("节点数"))
    by_status = serializers.DictField(help_text=_("按状态统计"), child=serializers.IntegerField())
    versions = serializers.ListField(help_text=_("版本列表"), child=serializers.CharField())
    machine_count = serializers.IntegerField(help_text=_("机器数"))
    by_os = serializers.DictField(help_text=_("按操作系统统计"), child=serializers.IntegerField())
    by_sub_zone = serializers.DictField(help_text=_("按子园区统计"), child=serializers.IntegerField())
    by_device_class = serializers.DictField(help_text=_("按设备类型统计"), child=serializers.IntegerField())
    by_spec = serializers.DictField(help_text=_("按规格统计"), child=serializers.IntegerField())
    spec_details = serializers.DictField(help_text=_("规格详情"), child=EsSpecDetailSerializer())
    nodes = serializers.ListField(help_text=_("节点列表"), child=EsNodeSerializer())


class EsTopoOutputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    major_version = serializers.CharField(help_text=_("ES版本"))
    phase = serializers.CharField(help_text=_("集群状态"))
    region = serializers.CharField(help_text=_("所在地域"))
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾级别"))
    tags = serializers.ListField(help_text=_("标签列表"), child=serializers.CharField())
    cluster_entries = serializers.ListField(help_text=_("集群入口列表"), child=EsClusterEntrySerializer())
    master_instances = EsRoleStatsSerializer(help_text=_("Master节点统计"))
    hot_instances = EsRoleStatsSerializer(help_text=_("Hot节点统计"))
    cold_instances = EsRoleStatsSerializer(help_text=_("Cold节点统计"))
    client_instances = EsRoleStatsSerializer(help_text=_("Client节点统计"))


class SpecSearchInputSerializer(serializers.Serializer):
    spec_name = serializers.CharField(help_text=_("规格名称，支持模糊匹配，如 '16核32G'"))
    spec_cluster_type = serializers.CharField(
        help_text=_("规格集群类型，默认为 es"),
        required=False,
        default="es",
    )


class SpecOutputSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    spec_cluster_type = serializers.CharField(help_text=_("规格集群类型"))
    spec_machine_type = serializers.CharField(help_text=_("规格机器类型"))
    cpu = serializers.DictField(help_text=_("CPU规格"))
    mem = serializers.DictField(help_text=_("内存规格"))
    device_class = serializers.CharField(help_text=_("设备类型"))
    storage_spec = serializers.ListField(help_text=_("存储规格"))
    desc = serializers.CharField(help_text=_("规格描述"))
