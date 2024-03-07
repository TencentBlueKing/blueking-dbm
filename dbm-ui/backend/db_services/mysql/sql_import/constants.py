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

from blue_krill.data_types.enum import EnumField, StructuredEnum

BKREPO_SQLFILE_PATH = "mysql/sqlfile"

CACHE_SEMANTIC_TASK_FIELD = "{user}_{cluster_type}_semantic_check_task"
CACHE_SEMANTIC_AUTO_COMMIT_FIELD = "{bk_biz_id}_{root_id}_semantic_check_auto_commit"
CACHE_SEMANTIC_SKIP_PAUSE_FILED = "{bk_biz_id}_{root_id}_semantic_check_skip_pause"
SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME = 7 * 24 * 60 * 60

# 最大预览SQL文件大小200MB
MAX_PREVIEW_SQL_FILE_SIZE = 200 * 1024 * 1024
# 最大上传SQL文件大小1G
MAX_UPLOAD_SQL_FILE_SIZE = 1024 * 1024 * 1024


class SQLCharset(str, StructuredEnum):
    """sql语句的字符集类型"""

    DEFAULT = EnumField("default", _("DEFAULT"))
    UTF8 = EnumField("utf8", _("UTF8"))
    UTF8MB4 = EnumField("utf8mb4", _("UTF8MB4"))
    LATIN1 = EnumField("latin1", _("LATIN1"))
    GBK = EnumField("gbk", _("gbk"))
    GB2312 = EnumField("gb2312", _("gb2312"))


class SQLExecuteTicketMode(str, StructuredEnum):
    """
    SQL执行单据的执行模式
    """

    MANUAL = EnumField("manual", _("手动执行"))
    AUTO = EnumField("auto", _("自动执行"))
    TIMER = EnumField("timer", _("定时执行"))


class SQLImportMode(str, StructuredEnum):
    """
    SQL导入的模式
    """

    FILE = EnumField("file", _("文件上传"))
    MANUAL = EnumField("manual", _("手动输入"))
