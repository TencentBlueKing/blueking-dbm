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
import logging

from rest_framework import serializers

from backend.db_meta import validators

from .serializers import CommonSerializer

logger = logging.getLogger("root")


def validated_integer(data, min_value=None, max_value=None, allow_null=False) -> int:
    field = serializers.IntegerField(min_value=min_value, max_value=max_value, allow_null=allow_null)
    slz = CommonSerializer(data=data, field=field)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_str(
    data, min_length=None, max_length=None, allow_blank=False, allow_null=False, trim_whitespace=True
) -> str:
    field = serializers.CharField(
        min_length=min_length,
        max_length=max_length,
        trim_whitespace=trim_whitespace,
        allow_blank=allow_blank,
        allow_null=allow_null,
    )
    slz = CommonSerializer(data=data, field=field)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_ip(data, allow_null=False, allow_blank=False) -> str:
    field = serializers.IPAddressField(allow_null=allow_null, allow_blank=allow_blank)
    slz = CommonSerializer(data=data, field=field)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


class _DomainField(serializers.CharField):
    def __init__(self, **kwargs):
        super(_DomainField, self).__init__(**kwargs)

    def run_validators(self, value):
        if not validators.domain(value):
            raise serializers.ValidationError("{} not a valid domain".format(value))

        super(_DomainField, self).run_validators(value)


def validated_domain(data, allow_null=False, allow_blank=False) -> str:
    field = _DomainField(allow_blank=allow_blank, allow_null=allow_null, trim_whitespace=True)
    slz = CommonSerializer(data=data, field=field)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_integer_list(data, min_value=None, max_value=None, allow_emtpy=True, allow_null=True):
    slz = serializers.ListSerializer(
        child=serializers.IntegerField(min_value=min_value, max_value=max_value),
        data=data,
        allow_empty=allow_emtpy,
        allow_null=allow_null,
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data
