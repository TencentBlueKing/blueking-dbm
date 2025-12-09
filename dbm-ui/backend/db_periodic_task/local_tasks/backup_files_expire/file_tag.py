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
from django.utils.translation import gettext as _

# backup file tag from table: bk_dbm_backup_server.tb_tag
BACKUP_FILE_TAG_TABLE = {
    "OTHER": {"file_savedays": 30, "tag_cn_name": _("未归类")},
    "BINLOG": {"file_savedays": 15, "tag_cn_name": _("BINLOG")},
    "MYSQL_FULL_BACKUP": {"file_savedays": 25, "tag_cn_name": _("MYSQL全备")},
    "ORACLE": {"file_savedays": 25, "tag_cn_name": _("ORACLE全备")},
    "OSDATA": {"file_savedays": 30, "tag_cn_name": _("脚本备份")},
    "INCREMENT_BACKUP": {"file_savedays": 15, "tag_cn_name": _("增量备份")},
    "LOG": {"file_savedays": 90, "tag_cn_name": _("普通日志备份")},
    "REDIS_FULL": {"file_savedays": 25, "tag_cn_name": _("REDIS_AOF")},
    "MONGO_INCR_BACKUP": {"file_savedays": 15, "tag_cn_name": _("OPLOG增量备份")},
    "REDIS_BINLOG": {"file_savedays": 15, "tag_cn_name": _("REDIS_BINLOG")},
    "DBFILE1M": {"file_savedays": 30, "tag_cn_name": _("DB1个月备份")},
    "DBFILE3M": {"file_savedays": 90, "tag_cn_name": _("DB3个月备份")},
    "DBFILE6M": {"file_savedays": 180, "tag_cn_name": _("DB6个月备份")},
    "DBFILE1Y": {"file_savedays": 365, "tag_cn_name": _("DB1年备份")},
    "DBFILE2Y": {"file_savedays": 730, "tag_cn_name": _("DB2年备份")},
    "DBFILE3Y": {"file_savedays": 1095, "tag_cn_name": _("DB3年备份")},
    "DBFILE10Y": {"file_savedays": 3650, "tag_cn_name": _("DB10年备份")},
    "DBFILE": {"file_savedays": 1098, "tag_cn_name": _("DB3年备份")},
}
