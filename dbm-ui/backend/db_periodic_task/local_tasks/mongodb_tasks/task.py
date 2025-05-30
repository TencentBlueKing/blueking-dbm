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

from .check_exporter import CheckMongodbUpMetricTask
from .check_backup import CheckMongoBackupRecordTask

logger = logging.getLogger("celery")

"""
    register_periodic_task 注册新的周期任务注意
    1. 通过装饰器注册周期任务
    2. import到 ../__init__.py
"""


@register_periodic_task(run_every=crontab(minute=1, hour=7))
def mongodb_backup_check_task():
    """
    mongodb 备份巡检.
    """
    CheckMongoBackupRecordTask().start()


@register_periodic_task(run_every=crontab(minute=1, hour="*/2"))
def mongodb_metric_check_task():
    """
    mongodb exporter巡检
    """
    CheckMongodbUpMetricTask().start()
