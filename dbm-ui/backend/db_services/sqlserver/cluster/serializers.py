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


class GetDBForDrsSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    db_list = serializers.ListField(help_text=_("db列表"), child=serializers.CharField())
    ignore_db_list = serializers.ListField(help_text=_("忽略db列表"), child=serializers.CharField(allow_blank=True))


class GetDBForDrsResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ["db1", "db2", "db3"]}


class ImportDBStructSerializer(GetDBForDrsSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    db_excel = serializers.FileField(help_text=_("构造DB的excel文件"))
    db_list = serializers.CharField(help_text=_("db列表(逗号分隔)"))
    ignore_db_list = serializers.CharField(help_text=_("忽略db列表(逗号分割)"))

    def validate(self, attrs):
        attrs["db_list"] = attrs["db_list"].split(",")
        attrs["ignore_db_list"] = attrs["ignore_db_list"].split(",")
        return attrs


class ImportDBStructResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": [{"db_name": "a", "target_db_name": "b", "rename_db_name": "c"}]}


class MultiGetDBForDrsSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("集群ID"))
    db_list = serializers.ListField(help_text=_("db列表"), child=serializers.CharField())
    ignore_db_list = serializers.ListField(help_text=_("忽略db列表"), child=serializers.CharField())


class MultiGetDBForDrsResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"1": ["db1", "db2", "db3"]}}


class CheckDBExistSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    db_list = serializers.ListField(help_text=_("db列表"), child=serializers.CharField())


class CheckDBExistResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"db1": True, "db2": False}}
