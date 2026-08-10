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

from backend.db_meta.enums import ClusterType


class PulsarBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class PulsarNoArgsInputSerializer(serializers.Serializer):
    """
    无需入参的工具，如查询当前登录用户负责的业务（用户身份由服务端从认证态获取）。

    这里保留一个可选字段而非完全空的序列化器：完全空会导致 drf-spectacular 不生成
    requestBody，而 mcp-discovery 依赖 requestBody 存在，缺失会导致工具发现失败。
    """

    bk_biz_id = serializers.IntegerField(
        help_text=_("业务ID（本工具无需传入，按当前调用用户返回其负责的业务）"),
        required=False,
        allow_null=True,
    )


class PulsarBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名"))


class PulsarBizDetailSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class PulsarClusterInputSerializer(serializers.Serializer):
    # 与 pulsar-toolbox/metrics/bill 各 server 的入参保持一致，统一用 cluster_domain
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class PulsarClusterOutputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    pulsar_version = serializers.CharField(help_text=_("Pulsar版本"))
    region = serializers.CharField(help_text=_("地域"))
    broker_count = serializers.IntegerField(help_text=_("Broker节点数"))
    bookkeeper_count = serializers.IntegerField(help_text=_("BookKeeper节点数"))
    zookeeper_count = serializers.IntegerField(help_text=_("Zookeeper节点数"))


class PulsarNodeSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("节点IP"))
    bk_host_id = serializers.IntegerField(help_text=_("主机ID，缩容/替换单据需要"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    port = serializers.IntegerField(help_text=_("服务端口"))
    instance_id = serializers.IntegerField(help_text=_("实例ID"))
    machine_type = serializers.CharField(help_text=_("机器类型"))
    status = serializers.CharField(help_text=_("实例状态"))
    device_class = serializers.CharField(help_text=_("设备类型"))
    spec = serializers.DictField(help_text=_("规格详情"), required=False)


class PulsarRoleInstancesSerializer(serializers.Serializer):
    """单个角色（broker/bookkeeper/zookeeper）下的实例汇总"""

    node_count = serializers.IntegerField(help_text=_("节点数"))
    by_status = serializers.DictField(help_text=_("按实例状态统计"))
    versions = serializers.ListField(help_text=_("版本列表"))
    machine_count = serializers.IntegerField(help_text=_("机器数"))
    by_os = serializers.DictField(help_text=_("按操作系统统计"))
    by_sub_zone = serializers.DictField(help_text=_("按地域-园区统计"))
    by_device_class = serializers.DictField(help_text=_("按设备类型统计"))
    by_spec = serializers.DictField(help_text=_("按规格统计"))
    spec_details = serializers.DictField(help_text=_("规格详情"))
    nodes = serializers.ListSerializer(child=PulsarNodeSerializer(), help_text=_("节点列表"))


class PulsarTopoOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    region = serializers.CharField(help_text=_("所在地域"))
    major_version = serializers.CharField(help_text=_("Pulsar版本"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    phase = serializers.CharField(help_text=_("集群阶段(启用/禁用)"))
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾level"))
    tags = serializers.ListField(help_text=_("集群标签"))
    cluster_entries = serializers.ListField(help_text=_("集群访问入口"))
    broker_instances = PulsarRoleInstancesSerializer(help_text=_("Broker节点汇总"))
    bookkeeper_instances = PulsarRoleInstancesSerializer(help_text=_("BookKeeper节点汇总"))
    zookeeper_instances = PulsarRoleInstancesSerializer(help_text=_("Zookeeper节点汇总"))


class SpecSearchInputSerializer(serializers.Serializer):
    spec_name = serializers.CharField(help_text=_("规格名称，支持模糊匹配，如 '16核32G'"))
    spec_cluster_type = serializers.CharField(
        help_text=_("规格集群类型，默认为 pulsar"),
        required=False,
        default=ClusterType.Pulsar.value,
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
