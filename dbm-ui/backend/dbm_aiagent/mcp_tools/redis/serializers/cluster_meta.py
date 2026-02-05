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

from backend.db_meta.enums import InstanceStatus


class RedisAddrSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))


class InstancePortSerializer(serializers.Serializer):
    port = serializers.CharField(help_text=_("实例端口"))


class RedisBizDetailSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    app_name = serializers.CharField(help_text=_("业务中文名"))
    abbr = serializers.CharField(help_text=_("业务英文名"))


class RedisBizsListSerializer(serializers.Serializer):
    bizs = serializers.ListSerializer(child=RedisBizDetailSerializer(), help_text=_("业务列表"))


class RedisBaseInstanceSerializer(serializers.Serializer):
    address = RedisAddrSerializer(help_text=_("ip:port 形式的实例地址"))
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices(), help_text=_("实例状态"))
    machine_type = serializers.CharField(help_text=_("实例机器类型"))


class RedisEntrySerializer(RedisBaseInstanceSerializer):
    entry_type = serializers.CharField(help_text=_("访问方式"))
    entry_addr = serializers.CharField(help_text=_("访问地址"))


class RedisListInstsTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    ips = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True, help_text="可选的主机列表，支持 IP "
    )


class RedisTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class RedisHostInputSerializer(serializers.Serializer):
    """Redis主机列表序列化器"""

    ips = serializers.ListField(
        child=serializers.IPAddressField(protocol="both"), help_text=_("主机IP地址列表"), required=True
    )


class RedisHostClusterOutputSerializer(serializers.Serializer):
    """Redis拓扑输入序列化器"""

    immute_domain = serializers.CharField(max_length=255, help_text=_("集群域名"), required=True)
    instance_role = serializers.CharField(max_length=100, help_text=_("实例角色"), required=True)
    host = serializers.IPAddressField(protocol="both", help_text=_("主机IP地址"), required=True)


# class RedisBatchTopoInputSerializer(serializers.Serializer):
#     """Redis批量拓扑输入序列化器"""

#     hosts = serializers.ListField(child=serializers.CharField(), help_text=_("主机IP地址列表"), required=False)
#     instances = serializers.ListField(child=RedisTopoInputSerializer(), help_text=_("Redis实例列表"), required=False)

#     def validate(self, attrs):
#         """验证至少提供hosts或instances之一"""
#         if not attrs.get("hosts") and not attrs.get("instances"):
#             raise serializers.ValidationError(_("必须提供hosts或instances中的至少一个字段"))
#         return attrs


class RedisProxiesOutputSerializer(serializers.Serializer):
    sub_zone = serializers.CharField(help_text=_("地域-园区"))
    cls_name = serializers.CharField(help_text=_("设备名称"))
    address = serializers.CharField(help_text=_("实例地址"))
    status = serializers.CharField(help_text=_("实例状态"))
    version = serializers.CharField(help_text=_("实例版本"))


class RedisMastersOutputSerializer(serializers.Serializer):
    sub_zone = serializers.CharField(help_text=_("地域-园区"))
    cls_name = serializers.CharField(help_text=_("设备名称"))
    ip = serializers.CharField(help_text=_("主机IP"))
    ports = serializers.ListSerializer(child=InstancePortSerializer(), help_text=_("实例端口"))


class RedisMastersSummarySerializer(serializers.Serializer):
    masters = serializers.ListSerializer(child=RedisMastersOutputSerializer(), help_text=_("存储层实例汇总"))


class RedisProxiesSummarySerializer(serializers.Serializer):
    proxies = serializers.ListSerializer(child=RedisProxiesOutputSerializer(), help_text=_("接入层实例信息"))


class ClusterEntrySerializer(serializers.Serializer):
    """集群访问入口信息"""

    entry_type = serializers.CharField(help_text=_("入口类型，如 dns/clb/clbDns/polaris"))
    entry_addr = serializers.CharField(help_text=_("入口地址"))


class RedisInstancesTopoSerializer(serializers.Serializer):
    """存储实例拓扑统计信息"""

    node_count = serializers.IntegerField(help_text=_("存储节点总数"))
    by_status = serializers.DictField(child=serializers.IntegerField(), help_text=_("按状态分布统计，如 {'running': 112}"))
    versions = serializers.ListField(child=serializers.CharField(), help_text=_("版本列表"))
    machine_count = serializers.IntegerField(help_text=_("机器数量"))
    by_os = serializers.DictField(child=serializers.IntegerField(), help_text=_("按操作系统分布统计"))
    by_sub_zone = serializers.DictField(child=serializers.IntegerField(), help_text=_("按子Zone分布统计"))
    by_device_class = serializers.DictField(child=serializers.IntegerField(), help_text=_("按设备类型分布统计"))


class RedisClusterBasicOutputSerializer(serializers.Serializer):
    """集群基本信息完整输出序列化器"""

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


class RedisClusterStorageDepOutputSerializer(serializers.Serializer):
    redis_master = RedisInstancesTopoSerializer(help_text=_("Master实例统计"))
    redis_slave = RedisInstancesTopoSerializer(help_text=_("Slave实例统计"))


class RedisBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class RedisBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名"))


class RedisEmptyInputSerializer(serializers.Serializer):
    userid = serializers.CharField(help_text=_("占位符"))


class RedisClustersOutputSerializer(serializers.Serializer):
    # bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    # cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    # redis_version = serializers.CharField(help_text=_("Redis版本"))
    region = serializers.CharField(help_text=_("地域"))
    # proxy_count = serializers.IntegerField(help_text=_("proxy节点数"))
    # master_count = serializers.IntegerField(help_text=_("master节点数"))


class RedisTupleInfoSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    master = serializers.CharField(help_text=_("主节点"))
    slave = serializers.CharField(help_text=_("从节点"))
    proxy = serializers.CharField(help_text=_("Proxy节点"))


class RedisInstanceTupleSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    instances = serializers.ListSerializer(child=RedisTupleInfoSerializer(), help_text=_("实例关系对"))
