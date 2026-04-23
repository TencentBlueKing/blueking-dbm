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


class ListBizClustersInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"), default=None)
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("集群域名列表"), default=None)
    ips = serializers.ListField(child=serializers.CharField(), help_text=_("IP 列表"), default=None)
    instances = serializers.ListField(child=serializers.CharField(), help_text=_("ip:port 形式的实例列表"), default=None)


class ClusterBaseInfoSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    region = serializers.CharField(help_text=_("所在地域, 城市, city"))
    affinity = serializers.CharField(help_text=_("亲和性"))
    status = serializers.CharField(help_text=_("集群状态"))
    phase = serializers.CharField(help_text=_("集群生命周期状态"))
    creator = serializers.CharField(help_text=_("集群创建人"))
    dbas = serializers.ListField(child=serializers.CharField(), help_text=_("集群 DBA 列表"))
    # 集群标签以 tag_<key> 形式作为动态顶级字段返回，每个字段的值为 List[str]

    class Meta:
        # 允许动态字段透传
        pass

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 将 tag_ 开头的动态字段透传到输出中
        for key, value in instance.items():
            if key.startswith("tag_") and key not in ret:
                ret[key] = value
        return ret


class ListBizClustersOutputSerializer(serializers.Serializer):
    clusters = serializers.ListSerializer(child=ClusterBaseInfoSerializer(), help_text=_("集群列表"))
