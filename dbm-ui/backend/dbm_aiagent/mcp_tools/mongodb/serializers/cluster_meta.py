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


class MongoAddrSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))


class InstancePortSerializer(serializers.Serializer):
    port = serializers.CharField(help_text=_("实例端口"))


class MongoBizDetailSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class MongoTopoInputSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))


class MongoHostInputSerializer(serializers.Serializer):
    """MongoDB主机列表序列化器"""

    hosts = serializers.ListField(
        child=serializers.IPAddressField(protocol="both"), help_text=_("主机IP地址列表"), required=True
    )


class MongoHostClusterOutputSerializer(serializers.Serializer):
    """MongoDB拓扑输出序列化器"""

    immute_domain = serializers.CharField(max_length=255, help_text=_("集群域名"), required=True)
    instance_role = serializers.CharField(max_length=100, help_text=_("实例角色"), required=True)
    host = serializers.IPAddressField(protocol="both", help_text=_("主机IP地址"), required=True)


class MongoMongosOutputSerializer(serializers.Serializer):
    sub_zone = serializers.CharField(help_text=_("地域-园区"))
    cls_name = serializers.CharField(help_text=_("设备名称"))
    address = serializers.CharField(help_text=_("实例地址"))
    status = serializers.CharField(help_text=_("实例状态"))
    version = serializers.CharField(help_text=_("实例版本"))


class MongoShardOutputSerializer(serializers.Serializer):
    sub_zone = serializers.CharField(help_text=_("地域-园区"))
    cls_name = serializers.CharField(help_text=_("设备名称"))
    ip = serializers.CharField(help_text=_("主机IP"))
    ports = serializers.ListSerializer(child=InstancePortSerializer(), help_text=_("实例端口"))


class MongoShardsSummarySerializer(serializers.Serializer):
    shards = serializers.ListSerializer(child=MongoShardOutputSerializer(), help_text=_("分片实例汇总"))


class MongoMongosSummarySerializer(serializers.Serializer):
    mongos = serializers.ListSerializer(child=MongoMongosOutputSerializer(), help_text=_("Mongos实例信息"))


class ClusterEntrySerializer(serializers.Serializer):
    """集群访问入口信息"""

    entry_type = serializers.CharField(help_text=_("入口类型，如 dns/clb/clbDns/polaris"))
    entry_addr = serializers.CharField(help_text=_("入口地址"))


class StorageInstancesTopoSerializer(serializers.Serializer):
    """存储实例拓扑统计信息"""

    node_count = serializers.IntegerField(help_text=_("存储节点总数"))
    by_role = serializers.DictField(child=serializers.IntegerField(), help_text=_("按角色分布统计"))
    by_status = serializers.DictField(child=serializers.IntegerField(), help_text=_("按状态分布统计"))
    versions = serializers.ListField(child=serializers.CharField(), help_text=_("版本列表"))
    machine_count = serializers.IntegerField(help_text=_("机器数量"))
    by_os = serializers.DictField(child=serializers.IntegerField(), help_text=_("按操作系统分布统计"))
    by_sub_zone = serializers.DictField(child=serializers.IntegerField(), help_text=_("按子Zone分布统计"))
    by_device_class = serializers.DictField(child=serializers.IntegerField(), help_text=_("按设备类型分布统计"))


class ProxyInstancesTopoSerializer(serializers.Serializer):
    """代理实例拓扑统计信息"""

    node_count = serializers.IntegerField(help_text=_("代理节点总数"))
    by_status = serializers.DictField(child=serializers.IntegerField(), help_text=_("按状态分布统计"))
    versions = serializers.ListField(child=serializers.CharField(), help_text=_("版本列表"))
    machine_count = serializers.IntegerField(help_text=_("机器数量"))
    by_os = serializers.DictField(child=serializers.IntegerField(), help_text=_("按操作系统分布统计"))
    by_sub_zone = serializers.DictField(child=serializers.IntegerField(), help_text=_("按子Zone分布统计"))
    by_device_class = serializers.DictField(child=serializers.IntegerField(), help_text=_("按设备类型分布统计"))


class ClusterTopoOutputSerializer(serializers.Serializer):
    """集群拓扑信息完整输出序列化器"""

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    major_version = serializers.CharField(help_text=_("主版本号"))
    region = serializers.CharField(help_text=_("地域"))
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾要求"))
    tags = serializers.ListField(child=serializers.CharField(), help_text=_("标签列表"))
    cluster_entries = serializers.ListField(child=ClusterEntrySerializer(), help_text=_("集群访问入口列表"))

    storage_instances = StorageInstancesTopoSerializer(help_text=_("存储实例统计"))
    proxy_instances = ProxyInstancesTopoSerializer(help_text=_("代理/Mongos实例统计"))


class MongoBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class MongoEmptyInputSerializer(serializers.Serializer):
    userid = serializers.CharField(help_text=_("占位符"))


class MongoClustersOutputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    mongodb_version = serializers.CharField(help_text=_("MongoDB版本"))
    region = serializers.CharField(help_text=_("地域"))
    mongos_count = serializers.IntegerField(help_text=_("Mongos节点数"), required=False)
    shard_count = serializers.IntegerField(help_text=_("分片数"), required=False)
    storage_count = serializers.IntegerField(help_text=_("存储节点数"), required=False)


class MongoMetaInfoInputSerializer(serializers.Serializer):
    """根据 IP、IP:PORT 或集群域名查询 MongoDB 实例元数据的入参"""

    value = serializers.CharField(
        help_text=_("域名、IP 或 IP:PORT"),
        required=True,
        allow_blank=False,
    )


class MongoMetaItemSerializer(serializers.Serializer):
    """单条 MongoDB 实例元数据"""

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_host = serializers.CharField(help_text=_("主机 IP"))
    ip = serializers.CharField(help_text=_("IP 地址"))
    port = serializers.IntegerField(help_text=_("端口"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    app_name = serializers.CharField(help_text=_("应用名称"))
    shard = serializers.CharField(help_text=_("分片信息"))


class MongoMetaInfoOutputSerializer(serializers.Serializer):
    """get_meta_info 返回：meta_list + error"""

    meta_list = serializers.ListField(
        child=MongoMetaItemSerializer(),
        help_text=_("匹配的 MongoDB 实例元数据列表"),
    )
    error = serializers.CharField(help_text=_("错误信息，成功时为空"))
