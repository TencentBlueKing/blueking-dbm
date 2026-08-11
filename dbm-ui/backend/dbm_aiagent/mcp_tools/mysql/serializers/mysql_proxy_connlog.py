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


class ProxyConnlogInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(
        help_text=_("集群域名（必填）"),
    )
    instance_hosts = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("proxy 实例 IP 列表（必填），格式如 ['1.1.1.1', '2.2.2.2']"),
        min_length=1,
    )
    conn_user = serializers.CharField(
        help_text=_("连接用户名，可选过滤条件"),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )
    session_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("会话ID列表，可选过滤条件"),
        required=False,
        allow_null=True,
        default=None,
    )
    start_time = serializers.DateTimeField(
        help_text=_("查询起始时间，默认为当前时间往前 7 天"),
        required=False,
        default=None,
    )
    end_time = serializers.DateTimeField(
        help_text=_("查询结束时间，默认为当前时间"),
        required=False,
        default=None,
    )
    limit = serializers.IntegerField(
        help_text=_("每个 instance_host 返回的最大记录数，默认 50"),
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
        max_value=200,
    )


class ProxyConnlogRowSerializer(serializers.Serializer):
    conn_time = serializers.CharField(help_text=_("连接时间"))
    client_ip = serializers.CharField(help_text=_("客户端IP"), allow_null=True)
    conn_user = serializers.CharField(help_text=_("连接用户"), allow_null=True)
    session_id = serializers.IntegerField(help_text=_("会话ID"), allow_null=True)


class ProxyConnlogInstanceSerializer(serializers.Serializer):
    instance_host = serializers.CharField(help_text=_("proxy 实例 IP"))
    records = ProxyConnlogRowSerializer(many=True, help_text=_("连接记录列表"))
    total = serializers.IntegerField(help_text=_("该实例符合条件的总记录数"))


class ProxyConnlogOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instances = ProxyConnlogInstanceSerializer(many=True, help_text=_("按实例分组的连接记录"))
