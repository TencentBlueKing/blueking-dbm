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
import unicodedata
from typing import List

from django.utils.translation import gettext as _

from backend.db_services.mysql.sql_import.constants import MAX_UPLOAD_SQL_FILE_NAME_LENGTH
from backend.exceptions import ValidationError


def validate_sql_file_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or name in (".", "..")
        or "/" in name
        or "\\" in name
        or any(unicodedata.category(char) in ("Cc", "Cs") for char in name)
    ):
        raise ValidationError(_("SQL文件名必须为单个文件名，不能包含路径或控制字符：{}").format(repr(name)))
    if len(name) > MAX_UPLOAD_SQL_FILE_NAME_LENGTH:
        raise ValidationError(_("请保证sql文件[{}]的文件名不超过{}个字符").format(name, MAX_UPLOAD_SQL_FILE_NAME_LENGTH))
    if not name.lower().endswith(".sql"):
        raise ValidationError(_("请保证sql文件[{}]的后缀为.sql").format(name))
    return name


def validate_sql_file_list(names: List[str]) -> List[str]:
    if not names:
        raise ValidationError(_("SQL文件列表不能为空"))
    for name in names:
        validate_sql_file_name(name)
    return names


def validate_uploaded_sql_repo_path(path: str, root: str, bk_biz_id: str) -> str:
    """制品库相对路径只允许 {root}/{bk_biz_id}/{文件名.sql}。"""
    invalid = _("SQL文件路径必须为制品库中的单个.sql文件：{}").format(repr(path))
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or any(unicodedata.category(char) in ("Cc", "Cs") for char in path)
    ):
        raise ValidationError(invalid)
    root_parts = [part for part in root.strip("/").split("/") if part]
    parts = path.split("/")
    if len(parts) != len(root_parts) + 2 or parts[: len(root_parts)] != root_parts:
        raise ValidationError(invalid)
    if any(part in ("", ".", "..") for part in parts):
        raise ValidationError(invalid)
    if parts[-2] != str(bk_biz_id):
        raise ValidationError(invalid)
    validate_sql_file_name(parts[-1])
    return path
