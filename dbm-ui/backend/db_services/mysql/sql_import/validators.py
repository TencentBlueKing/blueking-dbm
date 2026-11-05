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
import re
import unicodedata

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_services.mysql.sql_import.constants import MAX_UPLOAD_SQL_FILE_NAME_LENGTH

# 文件名允许：字母、数字、中文、下划线、连字符、点
SQL_FILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\u4e00-\u9fa5.]+$")
# 路径允许：字母、数字、下划线、连字符，分段用单个斜杠连接。刻意不含点，避免 ".." 逃逸目录
SQL_FILE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*$")

MAX_SQL_FILE_PATH_LENGTH = 255
# 错误信息中展示的文件名最大长度，避免超长或含特殊字符的内容直接回显到前端
MAX_ERROR_DISPLAY_LENGTH = 50


def _display(value: str) -> str:
    """截断用于错误提示的原始值"""
    return value if len(value) <= MAX_ERROR_DISPLAY_LENGTH else f"{value[:MAX_ERROR_DISPLAY_LENGTH]}..."


def validate_sql_file_name(file_name: str, suffix: str = None) -> str:
    """
    校验 SQL 文件名合法性

    文件名最终会拼进制品库对象路径、作业平台下发地址，DBA 侧的校验脚本也会直接使用它，
    因此必须在服务端按白名单收敛。前端校验只能拦住正常操作，伪造请求无法拦截。

    @param file_name: 文件名，不含目录部分
    @param suffix: 期望后缀（如 .sql / .js），为空时只做通用校验
    @return: 校验通过的文件名
    """
    name = (file_name or "").strip()

    if not name:
        raise serializers.ValidationError(_("SQL 文件名不能为空"))

    if len(name) > MAX_UPLOAD_SQL_FILE_NAME_LENGTH:
        raise serializers.ValidationError(
            _("SQL 文件名[{}]超长，最多允许{}个字符").format(_display(name), MAX_UPLOAD_SQL_FILE_NAME_LENGTH)
        )

    if "/" in name or "\\" in name:
        raise serializers.ValidationError(_("SQL 文件名[{}]不允许包含路径分隔符").format(_display(name)))

    if ".." in name:
        raise serializers.ValidationError(_("SQL 文件名[{}]不允许包含 '..'").format(_display(name)))

    if name.startswith("."):
        raise serializers.ValidationError(_("SQL 文件名[{}]不允许以 '.' 开头").format(_display(name)))

    if any(char.isspace() or unicodedata.category(char) == "Cc" for char in name):
        raise serializers.ValidationError(_("SQL 文件名[{}]不允许包含空白或控制字符").format(_display(name)))

    if not SQL_FILE_NAME_PATTERN.fullmatch(name):
        raise serializers.ValidationError(_("SQL 文件名[{}]包含非法字符，仅允许字母、数字、中文、下划线、连字符和点").format(_display(name)))

    if suffix and not name.lower().endswith(suffix):
        raise serializers.ValidationError(_("SQL 文件名[{}]必须以{}结尾").format(_display(name), suffix))

    return name


def validate_sql_file_name_field(value: str) -> None:
    """Serializer 字段级校验器，仅做通用规则，后缀由上层按集群类型决定"""
    validate_sql_file_name(value)


def validate_sql_file_path(path: str) -> str:
    """
    校验文件在制品库中的目录路径

    路径由后端拼接生成（如 mysql/sqlfile/4），这里做纵深防御，避免上层数据被篡改后
    拼出可以逃逸到其它业务目录的访问路径。

    @param path: 制品库内的相对目录，首尾斜杠会被归一化掉
    @return: 校验通过并归一化后的路径
    """
    # 各 db 类型的路径常量写法不一致（如 oracle 带尾斜杠），统一归一化，避免拼出双斜杠
    value = (path or "").strip().strip("/")

    if not value:
        raise serializers.ValidationError(_("SQL 文件路径不能为空"))

    if len(value) > MAX_SQL_FILE_PATH_LENGTH:
        raise serializers.ValidationError(_("SQL 文件路径[{}]超长").format(_display(value)))

    if ".." in value:
        raise serializers.ValidationError(_("SQL 文件路径[{}]不允许包含 '..'").format(_display(value)))

    if not SQL_FILE_PATH_PATTERN.fullmatch(value):
        raise serializers.ValidationError(_("SQL 文件路径[{}]包含非法字符，仅允许字母、数字、下划线、连字符和斜杠").format(_display(value)))

    return value


def get_sql_file_suffix(cluster_type: str = None) -> str:
    """按集群类型返回允许的文件后缀"""
    if cluster_type == DBType.MongoDB.value:
        return ".js"

    return ".sql"
