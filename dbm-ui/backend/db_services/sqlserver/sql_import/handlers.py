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
import os
from typing import Any, Dict, List, Optional

from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.db_services.mysql.sql_import.handlers import SQLHandler as MySQLSQLHandler
from backend.db_services.sqlserver.sql_import.constants import BKREPO_SQLFILE_PATH


class SQLHandler(object):
    """
    封装sql导入相关处理操作
    """

    def __init__(self, bk_biz_id: int, context: Dict = None, cluster_type: str = ""):
        """
        @param bk_biz_id: 业务ID
        @param context: 上下文数据
        @param cluster_type: 集群类型
        """

        self.bk_biz_id = bk_biz_id
        self.context = context
        self.cluster_type = cluster_type

    @classmethod
    def upload_sql_file(
        cls, sql_content: str = None, sql_files: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, Any]]:
        """
        将sql文本或者sql文件上传到制品库
        @param sql_content: sql 语句内容
        @param sql_files: sql 语句文件
        """
        # 逻辑同mysql的sql文件上传，直接复用即可
        sql_file_info_list = MySQLSQLHandler.upload_sql_file(BKREPO_SQLFILE_PATH, sql_content, sql_files)
        return sql_file_info_list

    @staticmethod
    def grammar_check(
        sql_content: str = None, sql_filenames: List[str] = None, sql_files: List[InMemoryUploadedFile] = None
    ) -> Optional[Dict]:
        """
        sql 语法检查
        @param sql_content: sql内容
        @param sql_filenames: sql文件名(在制品库的路径，说明已经在制品库上传好了。目前是适配sql执行插件形式.)
        @param sql_files: sql文件
        """
        if sql_filenames:
            sql_file_info_list = [{"sql_path": filename} for filename in sql_filenames]
        else:
            sql_file_info_list = MySQLSQLHandler.upload_sql_file(BKREPO_SQLFILE_PATH, sql_content, sql_files)

        # 填充虚构sqlserver内容。
        for sql_file_info in sql_file_info_list:
            sql_path = sql_file_info["sql_path"]
            file_name = os.path.split(sql_path)[1]
            data = {
                file_name: {
                    "syntax_fails": "",
                    "highrisk_warnings": "",
                    "bancommand_warnings": "",
                    "content": sql_file_info.get("sql_content"),
                    "sql_path": sql_path,
                    "raw_file_name": sql_file_info.get("raw_file_name"),
                    "skip_check": "",
                }
            }

            return data
