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


class DorisNoArgsInputSerializer(serializers.Serializer):
    """
    无需入参的工具，如查询当前登录用户负责的业务（用户身份由服务端从认证态获取）。

    这里保留一个可选字段而非完全空的序列化器：完全空会导致 drf-spectacular 不生成
    requestBody，而 mcp-discovery 依赖 requestBody 存在，缺失会导致工具发现失败。
    """

    bk_biz_id = serializers.IntegerField(
        help_text=_("业务 ID（本工具无需传入，按当前调用用户返回其负责的业务）"),
        required=False,
        allow_null=True,
    )


class DorisBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))


class DorisBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名，支持模糊匹配"))


class DorisBizDetailSerializer(serializers.Serializer):
    """业务详情，字段与 common.impl.biz_helpers 的返回结构一致"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class DorisClusterInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("Doris 集群访问域名，对应元数据中的 immute_domain"))


class DorisClusterListOutputSerializer(serializers.Serializer):
    """集群列表项"""

    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    region = serializers.CharField(help_text=_("所在地域"))
    major_version = serializers.CharField(help_text=_("Doris 版本"))
    role_node_counts = serializers.DictField(
        help_text=_(
            "按节点角色的节点数，键为角色值（doris_follower / doris_observer / "
            "doris_backend_hot / doris_backend_warm / doris_backend_cold），值为节点数。"
            "未部署的角色不会出现在此字典中"
        )
    )


class DorisClusterEntrySerializer(serializers.Serializer):
    entry_type = serializers.CharField(help_text=_("访问入口类型"))
    entry_addr = serializers.CharField(help_text=_("访问入口地址"))


class DorisClusterOverviewOutputSerializer(serializers.Serializer):
    """集群概览。

    只返回统计信息，不含逐节点清单；使用量与水位请调用 doris-metrics 的指标工具。
    """

    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    major_version = serializers.CharField(help_text=_("Doris 版本"))
    phase = serializers.CharField(help_text=_("集群阶段"))
    region = serializers.CharField(help_text=_("所在地域"))
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾级别"))
    tags = serializers.ListField(help_text=_("集群标签，格式为 key:value"))
    cluster_entries = serializers.ListSerializer(child=DorisClusterEntrySerializer(), help_text=_("集群访问入口列表"))
    roles = serializers.DictField(
        help_text=_(
            "按节点角色的统计，键为角色值，值包含："
            "role_alias(角色中文名)、layer(所属层 fe/be)、node_count(节点数)、"
            "machine_count(机器数，按主机去重)、by_status(实例状态分布)、versions(版本清单)、"
            "by_spec(规格 ID 到机器数)、spec_details(规格 ID 到规格详情)、"
            "by_os(操作系统分布)、by_sub_zone(子 Zone 分布)、by_device_class(设备类型分布)。"
            "未部署的角色不会出现在此字典中"
        )
    )
    summary = serializers.DictField(
        help_text=_(
            "FE / BE 两层汇总，含 fe_node_count、fe_machine_count、be_node_count、"
            "be_machine_count、total_node_count、total_machine_count"
        )
    )


class DorisSpecSearchInputSerializer(serializers.Serializer):
    spec_name = serializers.CharField(help_text=_("规格名称，支持模糊匹配，如 '16核32G'"))


class DorisSpecOutputSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格 ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    spec_cluster_type = serializers.CharField(help_text=_("规格集群类型"))
    spec_machine_type = serializers.CharField(help_text=_("规格机器类型"))
    cpu = serializers.DictField(help_text=_("CPU 规格"))
    mem = serializers.DictField(help_text=_("内存规格"))
    device_class = serializers.ListField(help_text=_("机型列表"))
    storage_spec = serializers.ListField(help_text=_("磁盘规格"))
    desc = serializers.CharField(help_text=_("规格描述"), allow_blank=True, allow_null=True)
