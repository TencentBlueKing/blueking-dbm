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
from typing import List

from rest_framework import serializers

from backend.db_meta import validators

logger = logging.getLogger("root")


class _AtomSerializer(serializers.BaseSerializer):
    def __init__(self, data, field, *args, **kwargs):
        self.initial_data = data
        self.field = field
        super().__init__(*args, **kwargs)

    def run_validators(self, value):
        return self.field.run_validators(value)

    def to_internal_value(self, data):
        return self.field.to_internal_value(data)


# def validated_integer(data, min_value=None, max_value=None, allow_null=False) -> int:
#     field = serializers.IntegerField(min_value=min_value, max_value=max_value, allow_null=allow_null)
#     slz = _AtomSerializer(data=data, field=field, allow_null=allow_null)
#     slz.is_valid(raise_exception=True)
#     return slz.validated_data


# def validated_str(data, min_length=None, max_length=None, allow_blank=False, trim_whitespace=True) -> str:
#     field = serializers.CharField(
#         min_length=min_length, max_length=max_length, allow_blank=allow_blank, trim_whitespace=trim_whitespace
#     )
#     slz = _AtomSerializer(data=data, field=field)
#     slz.is_valid(raise_exception=True)
#     return slz.validated_data


# def validated_integer_list(data, min_value=None, max_value=None, allow_empty=True, allow_null=True) -> List[int]:
#     slz = serializers.ListSerializer(
#         child=serializers.IntegerField(min_value=min_value, max_value=max_value),
#         data=data,
#         allow_empty=allow_empty,
#         allow_null=allow_null,
#     )
#     slz.is_valid(raise_exception=True)
#     return slz.validated_data


def validated_str_list(
    data, min_length=None, max_length=None, allow_blank=False, trim_whitespace=True, allow_empty=True, allow_null=True
) -> List[str]:
    slz = serializers.ListSerializer(
        child=serializers.CharField(
            min_length=min_length, max_length=max_length, allow_blank=allow_blank, trim_whitespace=trim_whitespace
        ),
        data=data,
        allow_empty=allow_empty,
        allow_null=allow_null,
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_ipaddress_list(data, allow_empty=True, allow_null=True) -> List[str]:
    slz = serializers.ListSerializer(
        child=serializers.IPAddressField(), allow_empty=allow_empty, allow_null=allow_null, data=data
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


class _DomainField(serializers.CharField):
    def __init__(self, **kwargs):
        super(_DomainField, self).__init__(**kwargs)

    def run_validators(self, value):
        if not validators.domain(value):
            raise serializers.ValidationError("{} not a valid domain".format(value))

        super(_DomainField, self).run_validators(value)


def validated_domain(data, allow_blank=False, trim_whitespace=True) -> str:
    field = _DomainField(allow_blank=allow_blank, trim_whitespace=trim_whitespace)
    slz = _AtomSerializer(data=data, field=field)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_domain_list(
    data, allow_blank=False, trim_whitespace=True, allow_empty=True, allow_null=True
) -> List[str]:
    slz = serializers.ListSerializer(
        child=_DomainField(allow_blank=allow_blank, trim_whitespace=trim_whitespace),
        data=data,
        allow_empty=allow_empty,
        allow_null=allow_null,
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


# def validated_ip(data) -> str:
#     field = serializers.IPAddressField()
#     slz = _AtomSerializer(data=data, field=field)
#     slz.is_valid(raise_exception=True)
#     return slz.validated_data
