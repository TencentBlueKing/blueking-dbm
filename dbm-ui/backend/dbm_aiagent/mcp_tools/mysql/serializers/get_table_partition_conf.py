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


class GetTablePartitionConfInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=True)
    db_name = serializers.CharField(help_text=_("库名"), required=True)
    table_name = serializers.CharField(help_text=_("表名"), required=True)


class PartitionDefSerializer(serializers.Serializer):
    partition_name = serializers.CharField(help_text=_("分区名"))
    partition_description = serializers.CharField(help_text=_("分区边界值"), allow_null=True)


class TablePartitionConfSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("分区策略 ID"))
    partition_column = serializers.CharField(help_text=_("分区字段"), allow_null=True)
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"), allow_null=True)
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"), allow_null=True)
    expire_time = serializers.IntegerField(help_text=_("过期时间"), allow_null=True)
    dblikes = serializers.ListField(child=serializers.CharField(), help_text=_("库匹配规则"))
    tblikes = serializers.ListField(child=serializers.CharField(), help_text=_("表匹配规则"))
    disabled = serializers.BooleanField(help_text=_("是否禁用"))
    last_execute_status = serializers.CharField(help_text=_("最近执行状态"), allow_null=True, required=False)
    last_execute_time = serializers.CharField(help_text=_("最近执行时间"), allow_null=True, required=False)


class TableFactSerializer(serializers.Serializer):
    exists = serializers.BooleanField(help_text=_("表是否存在"))
    is_partitioned = serializers.BooleanField(help_text=_("是否为分区表"))
    create_sql = serializers.CharField(help_text=_("建表语句"), allow_blank=True)
    partition_defs = PartitionDefSerializer(many=True, help_text=_("分区定义列表"))
    message = serializers.CharField(help_text=_("说明信息，如暂不支持模糊查询"), allow_null=True, required=False)


class ClusterBriefSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))


class TargetTableSerializer(serializers.Serializer):
    db_name = serializers.CharField(help_text=_("库名"))
    table_name = serializers.CharField(help_text=_("表名"))


class GetTablePartitionConfOutputSerializer(serializers.Serializer):
    cluster = ClusterBriefSerializer(help_text=_("集群信息"))
    target = TargetTableSerializer(help_text=_("查询目标"))
    partition_conf = TablePartitionConfSerializer(help_text=_("分区配置"), allow_null=True)
    table_fact = TableFactSerializer(help_text=_("实例侧表信息"))
