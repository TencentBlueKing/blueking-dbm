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

from backend import constants
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models.instance import ProxyInstance, StorageInstance


class _StorageSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    port = serializers.IntegerField(min_value=1025, max_value=65535)
    name = serializers.CharField(max_length=64, required=False)
    db_version = serializers.CharField(max_length=64, required=False)
    is_stand_by = serializers.BooleanField(required=False)


class _StorageWithRoleSerializer(_StorageSerializer):
    instance_role = serializers.ChoiceField(choices=InstanceRole.get_choices())


class _StorageForUpdateSerializer(_StorageSerializer):
    instance_role = serializers.ChoiceField(choices=InstanceRole.get_choices(), required=False)
    status = serializers.ChoiceField(choices=InstanceStatus.get_choices(), required=False)


def validated_storage_with_role_list(data, allow_empty=True, allow_null=True) -> List:
    slz = serializers.ListSerializer(
        child=_StorageWithRoleSerializer(), data=data, allow_empty=allow_empty, allow_null=allow_null
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_storage_list(data, allow_empty=True, allow_null=True) -> List:
    slz = serializers.ListSerializer(
        child=_StorageSerializer(), data=data, allow_empty=allow_empty, allow_null=allow_null
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_storage_update(data, allow_empty=True, allow_null=True) -> List:
    slz = serializers.ListSerializer(
        child=_StorageForUpdateSerializer(), data=data, allow_empty=allow_empty, allow_null=allow_null
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validated_storage(data):
    slz = _StorageSerializer(data=data)
    slz.is_valid(raise_exception=True)
    return slz.validated_data


def validate_instance_in_biz(bk_biz_id: int, instance_list: List[str] = None) -> List[str]:
    """
    校验实例是否在本业务中
    :param bk_biz_id: 业务ID
    :param instance_list: 实例列表，实例表示---ip:port
    """

    instance_not_in_biz = []
    for instance in instance_list:
        ip, port = instance.split(constants.IP_PORT_DIVIDER)
        instance = StorageInstance.objects.filter(machine__ip=ip, port=port) or ProxyInstance.objects.filter(
            machine__ip=ip, port=port
        )
        if instance.first().bk_biz_id != bk_biz_id:
            instance_not_in_biz.append(instance)

    return instance_not_in_biz
