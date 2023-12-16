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
import validators
from rest_framework import serializers

from backend.db_meta import meta_validator


class DBHAInstanceRequestSerializer(serializers.Serializer):
    class AddressField(serializers.CharField):
        def to_internal_value(self, data):
            if not validators.ipv4(data) and not meta_validator.instance(data):
                raise serializers.ValidationError('"{}" is not a valid address'.format(data))

    logical_city_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=0), allow_null=True, allow_empty=True
    )
    address = serializers.ListField(child=AddressField(), allow_null=True, allow_empty=True)
    statuses = serializers.ListField(child=serializers.CharField(), allow_null=True, allow_empty=True)


class DBHAUpdateStatusRequestSerializer(serializers.Serializer):
    class UpdateStatusEleSerializer(serializers.Serializer):
        ip = serializers.IPAddressField()
        port = serializers.IntegerField(min_value=1025, max_value=65535)
        status = serializers.CharField()

    payloads = UpdateStatusEleSerializer(many=True, allow_null=False, allow_empty=False)


class DBHASwapRequestSerializer(serializers.Serializer):
    class SwapEleSerializer(serializers.Serializer):
        class SwapInstanceSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            port = serializers.IntegerField(min_value=1025, max_value=65535)

        instance1 = SwapInstanceSerializer()
        instance2 = SwapInstanceSerializer()

    payloads = SwapEleSerializer(many=True, allow_null=False, allow_empty=False)


class DBHATendisClusterSwapRequestSerializer(serializers.Serializer):
    class SwapEleSerializer(serializers.Serializer):
        class SwapInstanceSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            port = serializers.IntegerField(min_value=1025, max_value=65535)

        instance1 = SwapInstanceSerializer()
        instance2 = SwapInstanceSerializer()

    payloads = SwapEleSerializer(many=True, allow_null=False, allow_empty=False)
