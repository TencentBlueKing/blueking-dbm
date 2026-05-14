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


class SQLServerListDatabasesInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时查询集群内全部实例"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    order_by = serializers.ChoiceField(
        help_text=_("排序键，可选 total_size_mb（默认，找占用最大的库）/ " "data_size_mb（找数据文件最大的库）/ log_size_mb（找日志暴涨的库）"),
        choices=["total_size_mb", "data_size_mb", "log_size_mb"],
        required=False,
        default="total_size_mb",
    )
    order = serializers.ChoiceField(
        help_text=_("排序方向，asc 升序 / desc 降序，默认 desc"),
        choices=["asc", "desc"],
        required=False,
        default="desc",
    )


class SQLServerDatabaseRowSerializer(serializers.Serializer):
    database_id = serializers.IntegerField(help_text=_("数据库 ID"))
    database_name = serializers.CharField(help_text=_("数据库名"))
    state = serializers.CharField(help_text=_("数据库状态，例如 ONLINE/OFFLINE/RESTORING"))
    recovery_model = serializers.CharField(help_text=_("恢复模式 FULL/SIMPLE/BULK_LOGGED"))
    compatibility_level = serializers.IntegerField(help_text=_("兼容级别"))
    collation = serializers.CharField(help_text=_("排序规则"), allow_null=True)
    create_date = serializers.CharField(help_text=_("创建时间"), allow_null=True)
    is_read_only = serializers.IntegerField(help_text=_("是否只读，1/0"))
    data_size_mb = serializers.IntegerField(help_text=_("数据文件大小 MB"))
    log_size_mb = serializers.IntegerField(help_text=_("日志文件大小 MB"))


class SQLServerListDatabasesItemSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("实例地址 ip:port"))
    role = serializers.CharField(help_text=_("实例内部角色"))
    is_stand_by = serializers.BooleanField(help_text=_("是否 standby 角色"))
    databases = SQLServerDatabaseRowSerializer(
        many=True,
        help_text=_("数据库清单"),
    )
    database_count = serializers.IntegerField(help_text=_("数据库数量"))
    error_msg = serializers.CharField(
        help_text=_("单实例错误信息；为空字符串表示成功"),
        allow_blank=True,
    )


class SQLServerListDatabasesOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    results = SQLServerListDatabasesItemSerializer(
        many=True,
        help_text=_("实例数据库清单列表"),
    )
