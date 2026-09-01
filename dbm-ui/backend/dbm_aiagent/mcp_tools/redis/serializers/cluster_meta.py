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
        child=serializers.CharField(), required=False, allow_null=True, default=[], help_text="可选的主机列表，支持 IP "
    )
    page = serializers.IntegerField(help_text=_("页码，从1开始"), required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(
        help_text=_("每页数量，默认80，最大150"), required=False, default=80, min_value=1, max_value=150
    )


class RedisListStorageInstsInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    addrs = serializers.ListSerializer(
        child=RedisAddrSerializer(), required=False, allow_null=True, default=[], help_text="可选的实例列表 "
    )
    page = serializers.IntegerField(help_text=_("页码，从1开始"), required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(
        help_text=_("每页数量，默认80，最大150"), required=False, default=80, min_value=1, max_value=150
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


class RedisProxiesSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=_("Proxy节点总数"))
    page = serializers.IntegerField(help_text=_("当前页码"))
    page_size = serializers.IntegerField(help_text=_("每页数量"))
    proxies = serializers.ListSerializer(child=RedisProxiesOutputSerializer(), help_text=_("接入层实例信息"))


class StorageTupleSerializer(serializers.Serializer):
    """存储实例主从关系"""

    redis_master = serializers.CharField(help_text=_("主节点地址（IP:Port）"))
    redis_slave = serializers.CharField(help_text=_("从节点地址（IP:Port）"))


class ClusterStorageTuplesSerializer(serializers.Serializer):
    """集群存储节点主从关系响应"""

    total = serializers.IntegerField(help_text=_("主从关系对总数"))
    page = serializers.IntegerField(help_text=_("当前页码"))
    page_size = serializers.IntegerField(help_text=_("每页数量"))
    tuples = StorageTupleSerializer(many=True, help_text=_("主从关系列表"))


class ClusterEntrySerializer(serializers.Serializer):
    """集群访问入口信息"""

    entry_type = serializers.CharField(help_text=_("入口类型，如 dns/clb/clbDns/polaris"))
    entry_addr = serializers.CharField(help_text=_("入口地址"))


class RedisInstancesTopoSerializer(serializers.Serializer):
    """存储实例拓扑统计信息"""

    node_count = serializers.IntegerField(help_text=_("存储节点总数"))
    by_status = serializers.DictField(child=serializers.IntegerField(), help_text=_("按状态分布统计，如 {'running': 112}"))
    by_version = serializers.DictField(
        child=serializers.IntegerField(), help_text=_("按版本分布统计，如 {'6.2.7': 12, '7.0.5': 4}")
    )
    by_machine_type = serializers.DictField(
        child=serializers.IntegerField(), help_text=_("按机型分布统计，如 {'tendiscache': 8, 'twemproxy': 4}")
    )
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
    page = serializers.IntegerField(help_text=_("页码，从1开始"), required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(
        help_text=_("每页数量，默认80，最大150"), required=False, default=80, min_value=1, max_value=150
    )


class RedisBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名"))


class RedisEmptyInputSerializer(serializers.Serializer):
    userid = serializers.CharField(help_text=_("占位符"))


class RedisSingleClusterSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    region = serializers.CharField(help_text=_("地域"))


class RedisClustersOutputSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text=_("集群总数"))
    page = serializers.IntegerField(help_text=_("当前页码"))
    page_size = serializers.IntegerField(help_text=_("每页数量"))
    clusters = serializers.ListSerializer(child=RedisSingleClusterSerializer(), help_text=_("集群列表"))


class RedisTupleInfoSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    master = serializers.CharField(help_text=_("主节点"))
    slave = serializers.CharField(help_text=_("从节点"))
    proxy = serializers.CharField(help_text=_("Proxy节点"))


class RedisInstanceTupleSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    instances = serializers.ListSerializer(child=RedisTupleInfoSerializer(), help_text=_("实例关系对"))


class RedisInstancesInputSerializer(serializers.Serializer):
    """Redis实例列表序列化器"""

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    addrs = serializers.ListField(child=serializers.CharField(), help_text=_("实例地址列表"), required=True)


class BindEntrySerializer(serializers.Serializer):
    """绑定入口条目"""

    id = serializers.IntegerField(help_text=_("入口ID"))
    entry = serializers.CharField(help_text=_("入口域名"))


class InstanceDetailSerializer(serializers.Serializer):
    """实例详细信息"""

    address = serializers.CharField(help_text=_("实例地址（IP:Port）"))
    version = serializers.CharField(help_text=_("版本号"))
    status = serializers.CharField(help_text=_("运行状态"))
    instance_role = serializers.CharField(help_text=_("实例角色（如 redis_slave、twemproxy）"))
    machine_type = serializers.CharField(help_text=_("机器类型（如 tendiscache、proxy）"))
    cluster_type = serializers.CharField(help_text=_("集群类型（如 TwemproxyRedisInstance）"))
    sub_zone = serializers.CharField(help_text=_("子区域（如 上海-松江）"))
    cls_name = serializers.CharField(help_text=_("规格名称（如 SA3.4XLARGE64）"))
    bind_entries = BindEntrySerializer(many=True, help_text=_("绑定的入口列表"))


class ClusterInstancesDetailSerializer(serializers.Serializer):
    """集群实例详情响应"""

    instances = InstanceDetailSerializer(many=True, help_text=_("实例列表"))
