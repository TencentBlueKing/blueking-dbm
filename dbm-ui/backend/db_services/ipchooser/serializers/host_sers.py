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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from .. import constants, mock_data
from . import base


class HostCheckRequestSer(base.ScopeSelectorBaseSer):
    mode = serializers.ChoiceField(
        help_text=_("模式"), choices=constants.ModeType.list_choices(), required=False, default=constants.ModeType.ALL
    )
    ip_list = serializers.ListField(
        help_text=_("IPv4 列表"),
        child=serializers.CharField(help_text=_("IPv4，支持的输入格式：`cloud_id:ip` / `ip`"), min_length=1),
        default=[],
        required=False,
    )
    ipv6_list = serializers.ListField(
        help_text=_("IPv6 列表"),
        child=serializers.CharField(help_text=_("IPv6，支持的输入格式：`cloud_id:ipv6` / `ipv6`"), min_length=1),
        default=[],
        required=False,
    )
    key_list = serializers.ListField(
        help_text=_("关键字列表"),
        child=serializers.CharField(help_text=_("关键字，解析出的`主机名`、`host_id` 等关键字信息"), min_length=1),
        default=[],
        required=False,
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_CHECK_REQUEST}


class HostCheckResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_CHECK_RESPONSE}


class HostDetailsRequestSer(base.ScopeSelectorBaseSer):
    mode = serializers.ChoiceField(
        help_text=_("模式"), choices=constants.ModeType.list_choices(), required=False, default=constants.ModeType.ALL
    )
    host_list = serializers.ListField(child=base.HostInfoWithMetaSer(), default=[])

    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_DETAILS_REQUEST}


class HostDetailsResponseSer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.API_HOST_DETAILS_RESPONSE}
