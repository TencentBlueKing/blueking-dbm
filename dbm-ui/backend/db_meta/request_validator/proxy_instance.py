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
from typing import List

from rest_framework import serializers

from backend.db_meta.enums import InstanceStatus


class _ProxySerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    port = serializers.IntegerField(min_value=1025, max_value=65535)
    version = serializers.CharField(max_length=64, required=False)


def validated_proxy_list(data, allow_empty=True, allow_null=True) -> List:
    slz = serializers.ListSerializer(
        child=_ProxySerializer(), data=data, allow_empty=allow_empty, allow_null=allow_null
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


class _ProxyWithStatusSerializer(_ProxySerializer):
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices())


def validated_proxy_update(data, allow_empty=True, allow_null=True) -> List:
    slz = serializers.ListSerializer(
        child=_ProxyWithStatusSerializer(), data=data, allow_null=allow_null, allow_empty=allow_empty
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data
