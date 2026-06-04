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

from django.db import connections, router
from django.db.models import Q
from django.utils import timezone

from backend.db_report.models.mysql_backup_result import MysqlBackupResult
from backend.db_report.models.mysql_binlog_backup_result import MysqlBinlogResult

from .file_tag import BACKUP_FILE_TAG_TABLE

logger = logging.getLogger("root")


def _batch_delete(model, where_clause, params, batch_size=1000):
    """
    批量删除，每次 DELETE LIMIT batch_size，避免大数据量一次性删除导致报错
    :param model: Django Model 类，用于获取表名和数据库连接
    :param where_clause: WHERE 条件子句（不含 WHERE 关键字）
    :param params: SQL 参数列表
    :param batch_size: 每批删除条数
    :return: 总删除行数
    """
    table_name = model._meta.db_table
    db_alias = router.db_for_write(model) or "default"
    total_deleted = 0
    while True:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {table_name} WHERE {where_clause} LIMIT %s",
                params + [batch_size],
            )
            rows_deleted = cursor.rowcount
        if rows_deleted == 0:
            break
        total_deleted += rows_deleted
        logger.info(f"==== batch deleted {total_deleted} records from {table_name} ====")
    return total_deleted


def clean_expired_mysql_backup_records():
    """
    清理过期的 MySQL 备份文件记录
    根据 backup_consistent_time + file_retention_tag 对应的保留天数，删除过期的记录
    """
    logger.info("==== start clean expired mysql backup records ====")

    deleted_count = 0
    error_count = 0

    # 遍历所有的备份文件标签
    TAGS = [
        "MYSQL_FULL_BACKUP",
        "DBFILE1M",
        "DBFILE3M",
        "DBFILE6M",
        "DBFILE1Y",
        "DBFILE2Y",
        "DBFILE3Y",
        "DBFILE10Y",
        "DBFILE",
    ]
    for tag_name in TAGS:
        try:
            tag_info = BACKUP_FILE_TAG_TABLE[tag_name]
            file_savedays = tag_info["file_savedays"]
            # 计算过期时间点：当前时间 - 保留天数
            expire_time = timezone.now() - timedelta(days=file_savedays + 1)

            logger.info(
                f"==== processing tag: {tag_name}, "
                f"retention days: {file_savedays}, expire time: {expire_time} ===="
            )

            # 查询该标签下所有过期的备份记录
            # backup_consistent_time < expire_time 表示已过期
            expired_records = MysqlBackupResult.objects.filter(
                Q(file_retention_tag=tag_name) & Q(backup_consistent_time__lt=expire_time)
            )

            count = expired_records.count()
            if count > 0:
                logger.info(f"==== found {count} expired records for tag {tag_name}, deleting in batches... ====")
                batch_deleted = _batch_delete(
                    MysqlBackupResult,
                    "file_retention_tag = %s AND backup_consistent_time < %s",
                    [tag_name, expire_time],
                )
                deleted_count += batch_deleted
                logger.info(f"==== successfully deleted {batch_deleted} expired records for tag {tag_name} ====")
            else:
                logger.info(f"==== no expired records found for tag {tag_name} ====")

        except Exception as e:
            error_count += 1
            logger.error(f"==== error cleaning expired records for tag {tag_name}: {e} ====")

    logger.info(
        f"==== clean expired mysql backup records completed, "
        f"total deleted: {deleted_count}, errors: {error_count} ===="
    )

    return {
        "deleted_count": deleted_count,
        "error_count": error_count,
        "status": "success" if error_count == 0 else "partial_success",
    }


def clean_expired_mysql_binlog_records():
    """
    清理过期的 MySQL Binlog 备份文件记录
    根据 stop_time + file_retention_tag 对应的保留天数，删除过期的记录
    """
    logger.info("==== start clean expired mysql binlog records ====")

    deleted_count = 0
    error_count = 0

    # 遍历所有的备份文件标签
    for tag_name in ["INCREMENT_BACKUP"]:
        try:
            tag_info = BACKUP_FILE_TAG_TABLE[tag_name]
            file_savedays = tag_info["file_savedays"]

            # 计算过期时间点：当前时间 - 保留天数
            expire_time = timezone.now() - timedelta(days=file_savedays + 1)

            logger.info(
                f"==== processing tag: {tag_name}, "
                f"retention days: {file_savedays}, expire time: {expire_time} ===="
            )

            # 查询该标签下所有过期的 binlog 备份记录
            # stop_time < expire_time 表示已过期
            expired_records = MysqlBinlogResult.objects.filter(
                Q(file_retention_tag=tag_name) & Q(file_mtime__lt=expire_time)
            )

            count = expired_records.count()
            if count > 0:
                logger.info(
                    f"==== found {count} expired binlog records for tag {tag_name}, deleting in batches... ===="
                )
                batch_deleted = _batch_delete(
                    MysqlBinlogResult,
                    "file_mtime < %s AND file_retention_tag= %s",
                    [expire_time, tag_name],
                )
                deleted_count += batch_deleted
                logger.info(
                    f"==== successfully deleted {batch_deleted} expired binlog records for tag {tag_name} ===="
                )
            else:
                logger.info(f"==== no expired binlog records found for tag {tag_name} ====")

        except Exception as e:
            error_count += 1
            logger.error(f"==== error cleaning expired binlog records for tag {tag_name}: {e} ====")

    logger.info(
        f"==== clean expired mysql binlog records completed, "
        f"total deleted: {deleted_count}, errors: {error_count} ===="
    )

    return {
        "deleted_count": deleted_count,
        "error_count": error_count,
        "status": "success" if error_count == 0 else "partial_success",
    }
