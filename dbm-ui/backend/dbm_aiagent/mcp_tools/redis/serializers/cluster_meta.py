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


class RedisBaseInstanceSerializer(serializers.Serializer):
    address = RedisAddrSerializer(help_text=_("ip:port 形式的实例地址"))
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices(), help_text=_("实例状态"))
    machine_type = serializers.CharField(help_text=_("实例机器类型"))


class RedisEntrySerializer(RedisBaseInstanceSerializer):
    entry_type = serializers.CharField(help_text=_("访问方式"))
    entry_addr = serializers.CharField(help_text=_("访问地址"))


class RedisTopoInputSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))


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


class RedisTopoOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    region = serializers.CharField(help_text=_("所在地域"))
    major_version = serializers.CharField(help_text=_("后端版本"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    proxy_count = serializers.IntegerField(help_text=_("Proxy节点数"))
    master_count = serializers.IntegerField(help_text=_("Master节点数"))
    cluster_entries = serializers.ListSerializer(child=RedisEntrySerializer(), help_text=_("集群连接地址"))


class RedisBizInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class RedisBizNameInputSerializer(serializers.Serializer):
    biz_name = serializers.CharField(help_text=_("业务英文名"))


class RedisEmptyInputSerializer(serializers.Serializer):
    userid = serializers.CharField(help_text=_("占位符"))


class RedisClustersOutputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"))
    redis_version = serializers.CharField(help_text=_("Redis版本"))
    region = serializers.CharField(help_text=_("地域"))
    proxy_count = serializers.IntegerField(help_text=_("proxy节点数"))
    master_count = serializers.IntegerField(help_text=_("master节点数"))


class RedisTupleInfoSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    master = serializers.CharField(help_text=_("主节点"))
    slave = serializers.CharField(help_text=_("从节点"))
    proxy = serializers.CharField(help_text=_("Proxy节点"))


class RedisInstanceTupleSerializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    instances = serializers.ListSerializer(child=RedisTupleInfoSerializer(), help_text=_("实例关系对"))
