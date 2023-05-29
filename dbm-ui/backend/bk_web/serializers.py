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

from rest_framework import serializers

from backend.bk_web.constants import LEN_NORMAL
from backend.utils.string import i18n_str


class AuditedSerializer(serializers.Serializer):
    """
    信息记录序列化
    """

    creator = serializers.CharField(read_only=True, max_length=LEN_NORMAL)
    create_at = serializers.DateTimeField(read_only=True)
    updater = serializers.CharField(read_only=True, max_length=LEN_NORMAL)
    update_at = serializers.DateTimeField(read_only=True)


class TranslationSerializerMixin(serializers.Serializer):
    """
    翻译序列化器基类
    """

    @property
    def translated_fields(self):
        # 待翻译的字段，默认为空
        return []

    def to_representation(self, instance):
        instance = super().to_representation(instance)
        for translated_field in self.translated_fields:
            instance[translated_field] = i18n_str(instance[translated_field])

        return instance
