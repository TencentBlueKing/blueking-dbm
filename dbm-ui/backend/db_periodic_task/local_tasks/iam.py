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

from celery import shared_task
from celery.schedules import crontab

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.iam_app.dataclass import flush_groups_auth

logger = logging.getLogger("root")


@shared_task
def async_flush_groups_auth():
    flush_groups_auth()


@register_periodic_task(run_every=crontab(day_of_week="1", hour="12", minute="0"))
def auto_flush_groups_auth_task():
    """定时每周一中午12点刷新用户组权限"""
    flush_groups_auth()
    logger.info("flush groups auth task finished")
