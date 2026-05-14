# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

索引分析功能域 - serializers 共享基类

5 个工具的入参高度同构（cluster_domain + dbname + table + schema + address），
公用层都建立在这里。出参的"实例位置/库位置"四元组也抽出来。
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class IndexAnalysisBaseInputSerializer(serializers.Serializer):
    """索引分析类工具的公共入参（批量形态）。

    `tables` 一次传 1~20 张表，整批共用同一个 `schema`。
    出参里每张表会落到 `results[i]`，并附带 status（ok / not_found / error）。
    """

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dbname = serializers.CharField(
        help_text=_("目标数据库名，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
    )
    tables = serializers.ListField(
        child=serializers.CharField(
            help_text=_("表名，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
        ),
        min_length=1,
        max_length=20,
        help_text=_("目标表名列表，1~20 个；整批共用同一个 schema；列表内重复项会被去重并保持首次出现的顺序"),
    )
    schema = serializers.CharField(
        help_text=_("表所在 schema，默认 dbo；仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
        required=False,
        allow_blank=True,
        default="dbo",
    )
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省走 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class IndexAnalysisLocatorOutputSerializer(serializers.Serializer):
    """所有"按表分析"工具出参的顶层位置信息字段（批量形态）。

    每张表的具体业务字段移到 `results[i]` 中；顶层不再带 `table`。
    """

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))


class PerTableResultBaseSerializer(serializers.Serializer):
    """每张表结果项的公共字段（业务字段由子类追加）。"""

    table = serializers.CharField(help_text=_("表名"))
    status = serializers.ChoiceField(
        choices=["ok", "not_found", "error"],
        help_text=_("处理状态：ok=查询成功；not_found=表不存在或无对应数据；error=其他错误"),
    )
    error = serializers.CharField(
        help_text=_("status 非 ok 时的错误说明；ok 时为 null"),
        allow_null=True,
        allow_blank=True,
        required=False,
    )
