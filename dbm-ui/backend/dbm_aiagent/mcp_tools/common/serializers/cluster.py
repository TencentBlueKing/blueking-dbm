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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.db_services.dbbase.serializers import ClusterFilterSerializer


class GetClusterBaseInfoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.ListField(child=serializers.CharField(help_text=_("集群域名")))


class GetClusterBaseInfoOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))


class FilterClusterInputSerializer(serializers.Serializer):
    # 基础的集群过滤条件
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    cluster_ids = serializers.CharField(help_text=_("集群ID(逗号分割)"), required=False)
    cluster_type = serializers.CharField(help_text=_("集群类型"), required=False)
    db_type = serializers.CharField(help_text=_("DB类型"), required=False)
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=-1)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)

    def validate(self, attrs):
        attrs = ClusterFilterSerializer(self).validate(attrs)
        return attrs


class ClusterStatsSerializer(serializers.Serializer):
    """集群统计信息"""

    used = serializers.IntegerField(help_text=_("已使用容量"))
    total = serializers.IntegerField(help_text=_("总容量"))
    in_use = serializers.FloatField(help_text=_("使用率"))


class ClusterEntrySerializer(serializers.Serializer):
    """集群访问入口"""

    cluster_entry_type = serializers.CharField(help_text=_("入口类型"))
    entry = serializers.CharField(help_text=_("入口地址"))
    role = serializers.CharField(help_text=_("角色"))


class FilterClusterOutputSerializer(AuditedSerializer):
    """集群详细信息响应序列化器"""

    id = serializers.IntegerField(help_text=_("集群ID"))
    db_type = serializers.CharField(help_text=_("数据库类型"))
    phase = serializers.CharField(help_text=_("阶段"))
    phase_name = serializers.CharField(help_text=_("阶段名称"))
    status = serializers.CharField(help_text=_("状态"))
    cluster_time_zone = serializers.CharField(help_text=_("集群时区"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"), allow_blank=True)
    cluster_access_port = serializers.IntegerField(help_text=_("集群访问端口"))
    cluster_stats = ClusterStatsSerializer(help_text=_("集群统计信息"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_type_name = serializers.CharField(help_text=_("集群类型名称"))
    cluster_subzones = serializers.ListField(child=serializers.CharField(), help_text=_("集群子区域列表"), allow_empty=True)
    cluster_subzone_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text=_("集群子区域ID列表"), allow_empty=True
    )
    disaster_tolerance_level = serializers.CharField(help_text=_("容灾级别"))
    master_domain = serializers.CharField(help_text=_("主域名"), allow_blank=True)
    slave_domain = serializers.CharField(help_text=_("从域名"), allow_blank=True)
    cluster_entry = ClusterEntrySerializer(many=True, help_text=_("集群访问入口列表"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_biz_name = serializers.CharField(help_text=_("业务名称"))
    bk_cloud_id = serializers.IntegerField(help_text=_("管控区域ID"))
    bk_cloud_name = serializers.CharField(help_text=_("管控区域名称"))
    major_version = serializers.CharField(help_text=_("主版本号"))
    region = serializers.CharField(help_text=_("地域"))
    city = serializers.CharField(help_text=_("城市"))
    db_module_name = serializers.CharField(help_text=_("DB模块名称"), allow_blank=True)
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    tags = serializers.ListField(child=serializers.CharField(), help_text=_("标签列表"), allow_empty=True)
