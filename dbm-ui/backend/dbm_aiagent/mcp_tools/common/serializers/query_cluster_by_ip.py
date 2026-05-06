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


class QueryClusterByIpInputSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), required=False, default=0)


class ClusterInfoByIpSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    db_type = serializers.CharField(help_text=_("主机的 DB 类型"))
    machine_type = serializers.CharField(help_text=_("主机的机器类型"))
    ip = serializers.CharField(help_text=_("主机 IP"))
    bk_sub_zone = serializers.CharField(help_text=_("子 Zone"), allow_null=True)
    bk_sub_zone_id = serializers.IntegerField(help_text=_("子 Zone ID"))
    bk_city = serializers.CharField(help_text=_("IDC 城市名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bk_svr_device_cls_name = serializers.CharField(help_text=_("标准设备类型"), allow_blank=True)
    spec_id = serializers.IntegerField(help_text=_("虚拟规格 ID"))
    spec_name = serializers.CharField(help_text=_("虚拟规格名称"), allow_blank=True)
    disaster_tolerance_level = serializers.CharField(help_text=_("亲和性（容灾级别）"), allow_blank=True)
    ports = serializers.ListField(child=serializers.IntegerField(), help_text=_("关联实例端口列表"))
    instance_inner_roles = serializers.ListField(child=serializers.CharField(), help_text=_("关联实例角色列表"))


class QueryClusterByIpOutputSerializer(serializers.Serializer):
    clusters = serializers.ListSerializer(child=ClusterInfoByIpSerializer(), help_text=_("集群信息列表"))
