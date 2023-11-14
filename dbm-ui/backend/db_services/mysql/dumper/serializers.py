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

from backend.db_meta.models.dumper import DumperSubscribeConfig
from backend.db_meta.models.extra_process import ExtraProcessInstance


class DumperSubscribeConfigSerializer(serializers.ModelSerializer):
    class SubscribeInfoSerializer(serializers.Serializer):
        db_name = serializers.CharField(help_text=_("DB名称"))
        table_names = serializers.ListField(help_text=_("表名列表"), child=serializers.CharField())

    subscribe = SubscribeInfoSerializer()

    class Meta:
        model = DumperSubscribeConfig
        fields = "__all__"


class DumperInstanceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraProcessInstance
        fields = "__all__"


class VerifyDuplicateNamsSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("订阅配置名称"))
