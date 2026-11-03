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

from backend.db_services.mysql.sql_import.serializers import SQLGrammarCheckSerializer
from backend.db_services.mysql.sql_import.validators import validate_uploaded_sql_repo_path
from backend.db_services.oracle.sql_import.constants import BKREPO_ORACLE_SQLFILE_PATH

ORACLE_SQLFILE_ROOT = BKREPO_ORACLE_SQLFILE_PATH.split("/{")[0]


class OracleGrammarCheckSerializer(SQLGrammarCheckSerializer):
    sql_filenames = serializers.ListField(
        help_text=_("sql文件在制品库中的路径"),
        child=serializers.CharField(trim_whitespace=False),
        required=False,
        allow_empty=False,
    )

    def validate_sql_filenames(self, names):
        bk_biz_id = str(self.context["view"].kwargs["bk_biz_id"])
        for name in names:
            validate_uploaded_sql_repo_path(name, ORACLE_SQLFILE_ROOT, bk_biz_id)
        return names
