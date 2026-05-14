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


class SQLServerServerConfigSummaryInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时查询集群内全部实例"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class SQLServerConfigItemSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("配置项名称，例如 max server memory (MB)"))
    value = serializers.IntegerField(help_text=_("配置值（已设置但可能未生效）"), allow_null=True)
    value_in_use = serializers.IntegerField(help_text=_("当前生效值"), allow_null=True)
    minimum = serializers.IntegerField(help_text=_("允许最小值"), allow_null=True)
    maximum = serializers.IntegerField(help_text=_("允许最大值"), allow_null=True)
    is_dynamic = serializers.IntegerField(help_text=_("是否无需重启即可生效，1/0"))
    is_advanced = serializers.IntegerField(help_text=_("是否高级选项，1/0"))
    description = serializers.CharField(help_text=_("配置项描述"), allow_null=True)


class SQLServerServerConfigSummaryItemSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("实例地址 ip:port"))
    role = serializers.CharField(help_text=_("实例内部角色"))
    is_stand_by = serializers.BooleanField(help_text=_("是否 standby 角色"))
    configurations = SQLServerConfigItemSerializer(
        many=True,
        help_text=_("关键配置项白名单结果"),
    )
    error_msg = serializers.CharField(
        help_text=_("单实例错误信息；为空字符串表示成功"),
        allow_blank=True,
    )


class SQLServerServerConfigSummaryOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    results = SQLServerServerConfigSummaryItemSerializer(
        many=True,
        help_text=_("实例关键配置摘要列表"),
    )
