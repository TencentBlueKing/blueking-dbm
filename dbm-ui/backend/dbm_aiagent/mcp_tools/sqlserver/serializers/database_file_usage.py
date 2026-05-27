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


class SQLServerDatabaseFileUsageInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    databases = serializers.ListField(
        child=serializers.CharField(
            help_text=_("数据库名，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
        ),
        min_length=1,
        max_length=20,
        help_text=_("目标数据库名列表，1~20 个；列表内重复项会被去重并保持首次出现的顺序"),
    )
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省走 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class _FileDetailSerializer(serializers.Serializer):
    file_id = serializers.IntegerField(help_text=_("文件 ID"))
    file_name = serializers.CharField(help_text=_("逻辑文件名"))
    file_type = serializers.IntegerField(help_text=_("文件类型，0=数据文件(mdf/ndf) 1=日志文件(ldf)"))
    file_type_desc = serializers.CharField(help_text=_("文件类型描述，ROWS / LOG"))
    physical_name = serializers.CharField(help_text=_("物理文件路径"))
    allocated_mb = serializers.IntegerField(help_text=_("已分配空间 MB"))
    used_mb = serializers.IntegerField(help_text=_("已使用空间 MB"))
    used_pct = serializers.FloatField(help_text=_("单文件使用率百分比，例如 85.32 表示 85.32%"))
    max_size_mb = serializers.IntegerField(
        help_text=_("文件最大大小 MB；-1 表示无限增长"),
    )
    growth_desc = serializers.CharField(help_text=_("增长策略描述，例如 64MB / 10% / NONE"))


class _PerDatabaseResultSerializer(serializers.Serializer):
    database = serializers.CharField(help_text=_("数据库名"))
    status = serializers.ChoiceField(
        choices=["ok", "error"],
        help_text=_("处理状态：ok=查询成功；error=查询失败（库 OFFLINE/RESTORING/不存在等）"),
    )
    error = serializers.CharField(
        help_text=_("status 非 ok 时的错误说明；ok 时为 null"),
        allow_null=True,
        allow_blank=True,
        required=False,
    )
    files = _FileDetailSerializer(
        many=True,
        help_text=_("文件级使用率明细（含 mdf/ndf/ldf）；status 非 ok 时为空数组"),
        required=False,
    )
    data_allocated_mb = serializers.IntegerField(
        help_text=_("数据文件总分配空间 MB（所有 ROWS 文件加总）"),
        required=False,
    )
    data_used_mb = serializers.IntegerField(
        help_text=_("数据文件总已用空间 MB"),
        required=False,
    )
    data_used_pct = serializers.FloatField(
        help_text=_("数据文件整体使用率%（已用/已分配 * 100）"),
        allow_null=True,
        required=False,
    )
    log_allocated_mb = serializers.IntegerField(
        help_text=_("日志文件总分配空间 MB（所有 LOG 文件加总）"),
        required=False,
    )
    log_used_mb = serializers.IntegerField(
        help_text=_("日志文件总已用空间 MB"),
        required=False,
    )
    log_used_pct = serializers.FloatField(
        help_text=_("日志文件整体使用率%（已用/已分配 * 100）"),
        allow_null=True,
        required=False,
    )


class SQLServerDatabaseFileUsageOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    database_count = serializers.IntegerField(help_text=_("入参数据库数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的数据库数量"))
    results = _PerDatabaseResultSerializer(
        many=True,
        help_text=_("每个数据库的文件使用率结果，顺序与入参 databases 一致"),
    )
