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


class RecommendSpecInputSerializer(serializers.Serializer):
    """
    Recommend spec for hosts input serializer.
    根据主机信息推荐规格输入序列化器。
    """

    ip_list = serializers.ListField(
        child=serializers.IPAddressField(),
        help_text=_(
            "List of host IPs to query (max 100). "
            "主机 IP 列表，最多 100 个。"
            "Can be obtained from cluster topology or machine list queries. "
            "可从集群拓扑或机器列表查询获取。"
        ),
        max_length=100,
    )
    bk_cloud_id = serializers.IntegerField(
        help_text=_("Cloud area ID (default: 0 for direct connection). " "云区域 ID，默认 0 表示直连区域。"),
        default=0,
        required=False,
    )
    spec_name_keywords = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "Keywords for fuzzy matching spec names (default: ['标准', '推荐', 'standard']). "
            "规格名称关键字列表，用于模糊匹配（默认：['标准', '推荐', 'standard']）。"
        ),
        default=["标准", "推荐", "standard"],
        required=False,
    )


class HostRecommendationSerializer(serializers.Serializer):
    """
    Host recommendation detail serializer.
    主机推荐规格详情序列化器。
    """

    spec_id = serializers.IntegerField(help_text=_("Spec ID. 规格 ID。"))
    spec_name = serializers.CharField(help_text=_("Spec name. 规格名称。"))
    spec_cluster_type = serializers.CharField(help_text=_("Cluster type. 集群类型。"))
    spec_machine_type = serializers.CharField(help_text=_("Machine type. 机器类型。"))
    cpu = serializers.JSONField(help_text=_("CPU spec (min/max). CPU 规格（最小/最大）。"))
    mem = serializers.JSONField(help_text=_("Memory spec in GB (min/max). 内存规格（GB）（最小/最大）。"))
    device_class = serializers.JSONField(help_text=_("Allowed device classes. 允许的机型列表。"))
    storage_spec = serializers.JSONField(help_text=_("Storage specification. 存储规格。"))
    matched_hosts = serializers.ListField(
        child=serializers.CharField(), help_text=_("List of matched host IPs. 匹配的主机 IP 列表。")
    )


class FailedHostSerializer(serializers.Serializer):
    """
    Failed host detail serializer.
    失败主机详情序列化器。
    """

    ip = serializers.CharField(help_text=_("Host IP. 主机 IP。"))
    reason = serializers.CharField(help_text=_("Failure reason. 失败原因。"))


class RecommendSpecOutputSerializer(serializers.Serializer):
    """
    Recommend spec output serializer.
    推荐规格输出序列化器。
    """

    recommendations = serializers.ListField(
        child=HostRecommendationSerializer(),
        help_text=_(
            "List of recommended specs with matched hosts. "
            "推荐规格列表及匹配的主机。"
            "Grouped by spec_id, each spec contains a list of matched host IPs. "
            "按 spec_id 聚合，每个规格包含匹配的主机 IP 列表。"
        ),
    )
    failed_hosts = serializers.ListField(
        child=FailedHostSerializer(),
        help_text=_(
            "List of hosts that failed to get recommendations. "
            "无法获取推荐规格的主机列表。"
            "Format: [{'ip': '127.0.0.1', 'reason': 'host not found'}]"
        ),
    )
