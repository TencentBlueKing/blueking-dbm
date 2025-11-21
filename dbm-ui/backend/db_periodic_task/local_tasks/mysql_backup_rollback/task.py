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
from django.utils.translation import gettext as _

from backend.db_periodic_task.local_tasks import register_periodic_task

from .check_failed_task import check_mysql_backup_exercise_failed
from .gen_task import gen_rollback_task

logger = logging.getLogger("root")


@register_periodic_task(run_every=crontab(minute="*/3"))
def backup_data_recovery_task():
    logger.info("start backup data recovery task")
    gen_rollback_task()


@register_periodic_task(run_every=crontab(day_of_week="*", hour="10", minute="30"))
def mysql_backup_exercise_check_failed():
    """
    检查MySQL备份演练失败任务
    """
    logger.info(_("开始检查MySQL备份演练失败任务"))
    check_mysql_backup_exercise_failed()
