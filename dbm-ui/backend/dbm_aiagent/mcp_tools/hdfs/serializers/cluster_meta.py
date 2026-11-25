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

from backend.db_meta.enums import InstanceRole

HDFS_META_ROLE_CHOICES = sorted(
    [
        InstanceRole.HDFS_NAME_NODE.value,
        InstanceRole.HDFS_DATA_NODE.value,
        InstanceRole.HDFS_JOURNAL_NODE.value,
        InstanceRole.HDFS_ZOOKEEPER.value,
    ]
)


class HdfsNoArgsInputSerializer(serializers.Serializer):
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


class HdfsBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))


class HdfsBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名，支持模糊匹配"))


class HdfsBizDetailSerializer(serializers.Serializer):
    """业务详情，字段与 common.impl.biz_helpers 的返回结构一致"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class HdfsClusterInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("HDFS 集群访问域名，对应元数据中的 immute_domain"))


class HdfsClusterListOutputSerializer(serializers.Serializer):
    """集群列表项"""

    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    region = serializers.CharField(help_text=_("所在地域"))
    major_version = serializers.CharField(help_text=_("HDFS 版本"))
    role_node_counts = serializers.DictField(
        help_text=_(
            "按节点角色的节点数，键为角色值（hdfs_namenode / hdfs_datanode / "
            "hdfs_journalnode / hdfs_zookeeper），值为节点数。"
            "未部署的角色不会出现在此字典中。"
            "注意 hdfs_zookeeper / hdfs_journalnode / hdfs_namenode 三类实例部署在同一批 "
            "master 机器上，三者节点数之和不等于机器数"
        )
    )


class HdfsClusterEntrySerializer(serializers.Serializer):
    entry_type = serializers.CharField(help_text=_("访问入口类型"))
    entry_addr = serializers.CharField(help_text=_("访问入口地址"))


class HdfsClusterOverviewOutputSerializer(serializers.Serializer):
    """集群概览。

    只返回统计信息，不含逐节点清单；使用量与水位请调用 hdfs-metrics 的指标工具。
    """

    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    major_version = serializers.CharField(help_text=_("HDFS 版本"))
    phase = serializers.CharField(help_text=_("集群阶段"))
    region = serializers.CharField(help_text=_("所在地域"))
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾级别"))
    tags = serializers.ListField(help_text=_("集群标签，格式为 key:value"))
    cluster_entries = serializers.ListSerializer(child=HdfsClusterEntrySerializer(), help_text=_("集群访问入口列表"))
    roles = serializers.DictField(
        help_text=_(
            "按节点角色的统计，键为角色值（hdfs_namenode / hdfs_datanode / "
            "hdfs_journalnode / hdfs_zookeeper），值包含："
            "role_alias(角色中文名)、machine_type(所属机型 hdfs_master/hdfs_datanode)、node_count(实例数)、"
            "machine_count(机器数，按主机去重)、by_status(实例状态分布)、versions(版本清单)、"
            "by_spec(规格 ID 到机器数)、spec_details(规格 ID 到规格详情)、"
            "by_os(操作系统分布)、by_sub_zone(子 Zone 分布)、by_device_class(设备类型分布)。"
            "未部署的角色不会出现在此字典中，据此可判断集群是否具备 HA 条件"
        )
    )
    summary = serializers.DictField(
        help_text=_(
            "按 machine_type 汇总，含 by_machine_type（hdfs_master / hdfs_datanode 各自的 "
            "node_count、machine_count）、total_node_count、total_machine_count。"
            "total_machine_count 按全集群去重，不等于各 machine_type 机器数之和"
        )
    )


class HdfsClusterNodesInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("HDFS 集群访问域名，对应元数据中的 immute_domain"))
    instance_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=HDFS_META_ROLE_CHOICES),
        required=False,
        default=None,
        allow_null=True,
        help_text=_("节点角色过滤，可选 hdfs_namenode / hdfs_datanode / hdfs_journalnode / hdfs_zookeeper；留空返回全部角色"),
    )
    ips = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=None,
        allow_null=True,
        help_text=_("IP 过滤；用户只提供了 IP 时传入，用于反查 bk_host_id 等完整节点信息。留空不过滤"),
    )


class HdfsClusterNodeSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("节点 IP"))
    port = serializers.IntegerField(help_text=_("实例端口"))
    instance_id = serializers.IntegerField(help_text=_("实例 ID，即元数据中 StorageInstance 的主键，与前端实例列表口径一致"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    role_alias = serializers.CharField(help_text=_("角色中文名"))
    status = serializers.CharField(help_text=_("实例状态"))
    version = serializers.CharField(help_text=_("实例版本"), allow_blank=True, allow_null=True)
    bk_host_id = serializers.IntegerField(help_text=_("主机 ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_sub_zone = serializers.CharField(help_text=_("子 Zone"), allow_blank=True, allow_null=True)
    spec_id = serializers.IntegerField(help_text=_("机器规格 ID"), allow_null=True)


class HdfsClusterNodesOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    node_count = serializers.IntegerField(help_text=_("返回的实例数"))
    nodes = serializers.ListSerializer(
        child=HdfsClusterNodeSerializer(),
        help_text=_("实例明细，按角色、IP、端口排序；同一台 master 机器的 zk / jn / nn 是三个实例，会以同一 IP 出现多次"),
    )
    unmatched_ips = serializers.ListField(help_text=_("传入的 ips 中未在本集群（或所选角色）中找到的 IP"))


class HdfsSpecSearchInputSerializer(serializers.Serializer):
    spec_name = serializers.CharField(help_text=_("规格名称，支持模糊匹配，如 '16核32G'"))


class HdfsSpecOutputSerializer(serializers.Serializer):
    spec_id = serializers.IntegerField(help_text=_("规格 ID"))
    spec_name = serializers.CharField(help_text=_("规格名称"))
    spec_cluster_type = serializers.CharField(help_text=_("规格集群类型"))
    spec_machine_type = serializers.CharField(
        help_text=_("规格机器类型，hdfs_master 承载 Zookeeper/JournalNode/NameNode，hdfs_datanode 承载 DataNode")
    )
    cpu = serializers.DictField(help_text=_("CPU 规格"))
    mem = serializers.DictField(help_text=_("内存规格"))
    device_class = serializers.ListField(help_text=_("机型列表"))
    storage_spec = serializers.ListField(help_text=_("磁盘规格"))
    desc = serializers.CharField(help_text=_("规格描述"), allow_blank=True, allow_null=True)
