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

from dataclasses import asdict, dataclass
from typing import Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.db_services.mysql.sql_import.constants import BKREPO_SQLFILE_PATH, SQLCharset


@dataclass
class SQLMeta:
    """sql导入的元信息"""

    sql_content: str = None
    sql_files: List[InMemoryUploadedFile] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "SQLMeta":
        return cls(**init_data)


@dataclass
class SQLExecuteMeta:
    """sql执行的元信息"""

    ticket_type: str
    created_by: str = ""
    bk_biz_id: str = ""

    path: str = BKREPO_SQLFILE_PATH
    charset: str = SQLCharset.DEFAULT.value
    cluster_ids: list = None
    execute_objects: list = None
    execute_sql_files: list = None
    execute_db_infos: list = None
    ticket_mode: dict = None
    highrisk_warnings: dict = None
    backup: list = None
    import_mode: str = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "SQLExecuteMeta":
        return cls(**init_data)


@dataclass
class SemanticOperateMeta:
    """语义检查相关操作涉及的元信息"""

    user: str = ""
    root_id: str = ""
    task_ids: List[str] = None
    is_auto_commit: bool = False
    is_skip_pause: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "SemanticOperateMeta":
        return cls(**init_data)
