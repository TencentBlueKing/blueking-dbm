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
from backend.db_meta.models import AppCache, Cluster, DBModule, Spec


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
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = MetadataImportDBModuleField(help_text=_("模块ID"), cluster_type=ClusterType.TenDBHA.value)
    proxy_spec_id = MetadataImportSpecField(
        help_text=_("代理层规格ID"), cluster_type=ClusterType.TenDBHA.value, machine_type=MachineType.PROXY.value
    )
    storage_spec_id = MetadataImportSpecField(
        help_text=_("存储层规格ID"), cluster_type=ClusterType.TenDBHA.value, machine_type=MachineType.BACKEND.value
    )

    def validate(self, attrs):
        return attrs


class MySQLStandardSerializer(serializers.Serializer):
    bk_biz_id = BizChoiceField(help_text=_("业务ID"))
    immute_domains = serializers.CharField(help_text=_("集群域名(多个域名用空格分隔)"))

    def validate(self, attrs):
        domain_list = attrs.pop("immute_domains").split(",")
        cluster_ids = list(Cluster.objects.filter(immute_domain__in=domain_list).values_list("id", flat=True))
        attrs["cluster_ids"] = cluster_ids
        return attrs
