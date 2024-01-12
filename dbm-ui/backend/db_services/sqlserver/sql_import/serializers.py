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

from backend.db_services.mysql.sql_import import mock_data
from backend.exceptions import ValidationError


class SQLUploadSerializer(serializers.Serializer):
    sql_content = serializers.CharField(help_text=_("sql语句"), required=False)
    sql_files = serializers.ListField(
        help_text=_("sql文件列表"), child=serializers.FileField(help_text=_("sql文件"), required=False), required=False
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_GRAMMAR_CHECK_REQUEST_DATA}

    def validate(self, attrs):
        if not (attrs.get("sql_content") or attrs.get("sql_files")):
            raise ValidationError(_("不允许语法检查的sql的内容为空！"))

        for file in attrs.get("sql_files", []):
            if file.name.rsplit(".")[-1] != "sql":
                raise ValidationError(_("请保证sql文件[{}]的后缀为.sql").format(file.name))

        return attrs
