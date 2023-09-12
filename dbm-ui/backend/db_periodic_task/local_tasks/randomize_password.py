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

from backend.configuration.tasks.password import randomize_admin_password
from backend.db_periodic_task.local_tasks import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(day_of_week="*", hour="10", minute="3"))
def auto_randomize_password_daily():
    """每日随机化密码"""
    randomize_admin_password(if_async=True, range_type="randmize_daily")


@register_periodic_task(run_every=crontab(minute="*"))
def auto_randomize_password_expired():
    """当密码锁定到期，随机化密码"""
    randomize_admin_password(if_async=True, range_type="randmize_expired")
