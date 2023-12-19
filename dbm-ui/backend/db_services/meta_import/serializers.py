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

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, DBModule, Spec


class CustomChoiceField(serializers.ChoiceField):
    def __init__(self, choices, **kwargs):
        super().__init__(choices, **kwargs)
        self._choices_label_to_value = {value: key for key, value in self.choices.items()}

    def to_representation(self, value):
        return self._choices[value]

    def to_internal_value(self, data):
        return self._choices_label_to_value[data]


class MetadataImportDBModuleField(CustomChoiceField):
    model = DBModule

    def __init__(self, cluster_type, **kwargs):
        choices = self.model.get_choices_with_filter(cluster_type=cluster_type)
        super().__init__(choices, **kwargs)


class MetadataImportSpecField(CustomChoiceField):
    model = Spec

    def __init__(self, cluster_type, machine_type, **kwargs):
        choices = self.model.get_choices_with_filter(cluster_type=cluster_type, machine_type=machine_type)
        super().__init__(choices, **kwargs)


class BizChoiceField(CustomChoiceField):
    model = AppCache

    def __init__(self, **kwargs):
        choices = self.model.get_choices()
        super().__init__(choices, **kwargs)


class MySQLHaMetadataImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=_("元数据json文件"))
    bk_biz_id = BizChoiceField(help_text=_("业务"))
    db_module_id = MetadataImportDBModuleField(help_text=_("模块ID"), cluster_type=ClusterType.TenDBHA.value)
    proxy_spec_id = MetadataImportSpecField(
        help_text=_("代理层规格ID"), cluster_type=ClusterType.TenDBHA.value, machine_type=MachineType.PROXY.value
    )
    storage_spec_id = MetadataImportSpecField(
        help_text=_("存储层规格ID"), cluster_type=ClusterType.TenDBHA.value, machine_type=MachineType.BACKEND.value
    )

    def validate(self, attrs):
        return attrs


class MySQLHaStandardSerializer(serializers.Serializer):
    bk_biz_id = BizChoiceField(help_text=_("业务ID"))
    file = serializers.FileField(help_text=_("域名列表文件"))

    def validate(self, attrs):
        return attrs


class TendbClusterStandardSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), default=0)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("待标准的集群列表"))
    use_stream = serializers.BooleanField(help_text=_("是否使用mydumper流式备份迁移"), required=False, default=False)
    drop_before = serializers.BooleanField(help_text=_("导入到tdbctl前,是否先删除"), required=False, default=False)
    threads = serializers.IntegerField(help_text=_("业务ID"), required=False, default=0)
    use_mydumper = serializers.BooleanField(help_text=_("是否使用mydumper,myloader迁移"), required=False, default=True)

    def validate(self, attrs):
        return attrs
