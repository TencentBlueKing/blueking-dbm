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

from backend.db_meta.enums import MachineType


class _MachineSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    bk_biz_id = serializers.IntegerField(min_value=0)
    machine_type = serializers.ChoiceField(choices=MachineType.get_choices())  # serializers.CharField(cho)
    spec_id = serializers.IntegerField(required=False)
    spec_config = serializers.JSONField(required=False)


def validated_machine_create(data, allow_empty=True, allow_null=True) -> List:
    # for pl in data:  # 验证 bk_biz_id 在 db_meta 中存在
    #     App.objects.get(bk_biz_id=pl['bk_biz_id'])

    slz = serializers.ListSerializer(
        child=_MachineSerializer(), data=data, allow_empty=allow_empty, allow_null=allow_null
    )
    slz.is_valid(raise_exception=True)
    return slz.validated_data
