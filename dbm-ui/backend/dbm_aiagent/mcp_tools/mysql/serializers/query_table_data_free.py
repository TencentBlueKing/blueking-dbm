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


class QueryTableDataFreeInputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(
        help_text=_("集群 ID，与 cluster_domain 二选一"),
        required=False,
        allow_null=True,
    )
    cluster_domain = serializers.CharField(
        help_text=_("集群域名，与 cluster_id 二选一"),
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    dbname = serializers.CharField(
        help_text=_("库名，可选；不传则查询集群内所有非系统库中空洞大于 10GB 的表"),
        required=False,
        allow_blank=True,
        default="",
    )
    table_names = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("表名列表，可选；不传则不过滤表名"),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        cluster_id = attrs.get("cluster_id")
        cluster_domain = (attrs.get("cluster_domain") or "").strip()
        if cluster_id is None and not cluster_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 必须提供其一"))
        if cluster_id is not None and cluster_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 只能提供其一"))
        if cluster_domain:
            attrs["cluster_domain"] = cluster_domain
        return attrs


class QueryTableDataFreeRowSerializer(serializers.Serializer):
    table_schema = serializers.CharField(help_text=_("数据库名"))
    table_name = serializers.CharField(help_text=_("表名"))
    engine = serializers.CharField(help_text=_("存储引擎"))
    table_rows = serializers.IntegerField(help_text=_("预估行数"))
    data_size_gb = serializers.FloatField(help_text=_("数据大小 GB"))
    index_size_gb = serializers.FloatField(help_text=_("索引大小 GB"))
    data_free_gb = serializers.FloatField(help_text=_("空洞碎片 GB"))
    data_free_ratio_pct = serializers.FloatField(help_text=_("空洞碎片占比 %"))


class QueryTableDataFreeOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    address = serializers.CharField(help_text=_("查询实例地址 ip:port"))
    dbname = serializers.CharField(help_text=_("请求传入的库名（逻辑库名）"))
    tables = QueryTableDataFreeRowSerializer(many=True, help_text=_("表空洞查询结果"))
