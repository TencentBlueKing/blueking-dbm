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
from typing import Any, Dict, List

from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.db_services.mysql.sql_import.handlers import SQLHandler as MySQLSQLHandler
from backend.db_services.sqlserver.sql_import.constants import BKREPO_SQLSERVER_SQLFILE_PATH


class SQLHandler(object):
    """
    封装sql导入相关处理操作
    """

    @classmethod
    def upload_sql_file(
        cls, bk_biz_id: int, sql_content: str = None, sql_files: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, Any]]:
        """
        将sql文本或者sql文件上传到制品库
        @param bk_biz_id: 业务ID
        @param sql_content: sql 语句内容
        @param sql_files: sql 语句文件
        """
        # 逻辑同mysql的sql文件上传，直接复用即可
        upload_sql_file = BKREPO_SQLSERVER_SQLFILE_PATH.format(biz=bk_biz_id)
        sql_file_info_list = MySQLSQLHandler.upload_sql_file(upload_sql_file, sql_content, sql_files)
        return sql_file_info_list
