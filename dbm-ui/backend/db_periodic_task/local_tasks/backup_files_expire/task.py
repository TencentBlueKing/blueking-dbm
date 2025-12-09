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

from backend.db_periodic_task.local_tasks.register import register_periodic_task

from .clean_expired_backup import clean_all_expired_backup_records

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=0, hour=23))
def clean_expired_backup_records_task():
    """
    清理过期的备份文件记录（包括 MySQL 全备和 Binlog）
    每天凌晨3点执行
    """
    clean_all_expired_backup_records()
