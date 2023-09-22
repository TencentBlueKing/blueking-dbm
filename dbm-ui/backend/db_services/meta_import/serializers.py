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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.models import DBModule, Spec


class MetadataImportChoiceField(serializers.ChoiceField):
    """元数据导入的动态choice字段"""

    model = None

    def __init__(self, model, **kwargs):
        self.model = model
        choices = self.model.get_choices()
        super().__init__(choices, **kwargs)
        self._choices_label_to_value = {value: key for key, value in self.choices.items()}

    def to_representation(self, value):
        return self._choices[value]

    def to_internal_value(self, data):
        return self._choices_label_to_value[data]


class MySQLHaMetadataImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=_("元数据json文件"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = MetadataImportChoiceField(help_text=_("模块ID"), model=DBModule)
    proxy_spec_id = MetadataImportChoiceField(help_text=_("代理层规格ID"), model=Spec)
    storage_spec_id = MetadataImportChoiceField(help_text=_("存储层规格ID"), model=Spec)

    def validate(self, attrs):
        return attrs
