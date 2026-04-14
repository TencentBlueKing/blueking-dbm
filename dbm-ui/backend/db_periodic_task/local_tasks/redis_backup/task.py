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

from celery.schedules import crontab

from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import CheckBinlogBackupTask
from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import CheckFullBackupTask
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=0, hour=0))
def redis_full_backup_check_task():
    """Redis full backup check -- runs daily at 00:00."""
    try:
        total, normal, warning, abnormal = CheckFullBackupTask().start()
        logger.info(
            "redis_full_backup_check_task finished: total=%s normal=%s warning=%s abnormal=%s",
            total,
            normal,
            warning,
            abnormal,
        )
    except Exception:
        logger.exception("redis_full_backup_check_task failed")


@register_periodic_task(run_every=crontab(minute=30, hour=2))
def redis_binlog_backup_check_task():
    """Redis binlog backup check -- runs daily at 02:30."""
    try:
        total, normal, warning, abnormal = CheckBinlogBackupTask().start()
        logger.info(
            "redis_binlog_backup_check_task finished: total=%s normal=%s warning=%s abnormal=%s",
            total,
            normal,
            warning,
            abnormal,
        )
    except Exception:
        logger.exception("redis_binlog_backup_check_task failed")
