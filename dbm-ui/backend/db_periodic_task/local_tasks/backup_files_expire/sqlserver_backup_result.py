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
import logging
from datetime import timedelta
from typing import List

from django.db import connections, router
from django.db.models import Q
from django.utils import timezone

from backend.db_report.models.sqlserver_full_backup_result import SQLServerBackupResult
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult

from .file_tag import BACKUP_FILE_TAG_TABLE

logger = logging.getLogger("root")


class ExpiredBackupCleaner:
    """
    SQLServer 过期备份记录清理基类
    通用流程：遍历 tag -> 计算过期时间 -> 批量删除过期记录 -> 汇总日志
    子类只需要声明：model、tag字段名、时间字段名、tag列表、业务名（用于日志）
    """

    # 需要子类覆盖
    model = None
    tag_field: str = ""
    time_field: str = ""
    tags: List[str] = []
    biz_name: str = ""

    # 单批删除条数
    batch_size: int = 1000

    def _batch_delete(self, where_clause: str, params: list) -> int:
        """批量删除，每次 DELETE LIMIT batch_size，避免大数据量一次性删除导致报错"""
        table_name = self.model._meta.db_table
        db_alias = router.db_for_write(self.model) or "default"
        total_deleted = 0
        while True:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {table_name} WHERE {where_clause} LIMIT %s",
                    params + [self.batch_size],
                )
                rows_deleted = cursor.rowcount
            if rows_deleted == 0:
                break
            total_deleted += rows_deleted
            logger.info(f"==== batch deleted {total_deleted} records from {table_name} ====")
        return total_deleted

    def _clean_by_tag(self, tag_name: str) -> int:
        """清理单个 tag 下的过期记录，返回删除条数"""
        tag_info = BACKUP_FILE_TAG_TABLE[tag_name]
        file_savedays = tag_info["file_savedays"]
        # 计算过期时间点：当前时间 - 保留天数
        expire_time = timezone.now() - timedelta(days=file_savedays + 1)

        logger.info(
            f"==== processing tag: {tag_name}, " f"retention days: {file_savedays}, expire time: {expire_time} ===="
        )

        expired_records = self.model.objects.filter(
            Q(**{self.tag_field: tag_name}) & Q(**{f"{self.time_field}__lt": expire_time})
        )
        count = expired_records.count()
        if count == 0:
            logger.info(f"==== no expired {self.biz_name} records found for tag {tag_name} ====")
            return 0

        logger.info(
            f"==== found {count} expired {self.biz_name} records for tag {tag_name}, deleting in batches... ===="
        )
        batch_deleted = self._batch_delete(
            f"{self.tag_field} = %s AND {self.time_field} < %s",
            [tag_name, expire_time],
        )
        logger.info(
            f"==== successfully deleted {batch_deleted} expired {self.biz_name} records for tag {tag_name} ===="
        )
        return batch_deleted

    def run(self) -> dict:
        """执行清理流程"""
        logger.info(f"==== start clean expired sqlserver {self.biz_name} records ====")

        deleted_count = 0
        error_count = 0
        for tag_name in self.tags:
            try:
                deleted_count += self._clean_by_tag(tag_name)
            except Exception as e:
                error_count += 1
                logger.error(f"==== error cleaning expired {self.biz_name} records for tag {tag_name}: {e} ====")

        logger.info(
            f"==== clean expired sqlserver {self.biz_name} records completed, "
            f"total deleted: {deleted_count}, errors: {error_count} ===="
        )

        return {
            "deleted_count": deleted_count,
            "error_count": error_count,
            "status": "success" if error_count == 0 else "partial_success",
        }


# 共用的归档类 tag（按月/年保留）
ARCHIVE_TAGS = ["DBFILE1M", "DBFILE3M", "DBFILE6M", "DBFILE1Y", "DBFILE2Y", "DBFILE3Y", "DBFILE10Y", "DBFILE"]


class SQLServerBackupCleaner(ExpiredBackupCleaner):
    """SQLServer 全量备份清理"""

    model = SQLServerBackupResult
    tag_field = "backup_file_tag"
    time_field = "backup_end_time"
    tags = ["MSSQL_FULL_BACKUP", "OTHER"] + ARCHIVE_TAGS
    biz_name = "backup"


class SQLServerBinlogCleaner(ExpiredBackupCleaner):
    """SQLServer 事务日志备份清理"""

    model = SQLServerBinlogResult
    tag_field = "backup_file_tag"
    time_field = "backup_end_time"
    tags = ["INCREMENT_BACKUP", "OTHER"] + ARCHIVE_TAGS
    biz_name = "binlog"


def clean_expired_sqlserver_backup_records():
    """清理过期的 SQLServer 全量备份文件记录"""
    return SQLServerBackupCleaner().run()


def clean_expired_sqlserver_binlog_records():
    """清理过期的 SQLServer 事务日志备份文件记录"""
    return SQLServerBinlogCleaner().run()
