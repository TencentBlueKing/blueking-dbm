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
from celery.schedules import crontab

from backend.db_periodic_task.local_tasks.register import register_periodic_task

from .base import RedisRollbackExercise


@register_periodic_task(run_every=crontab(day_of_week="0", hour="12", minute="0"))
def init_redis_rollback_candidates():
    """
    Init candidates to exericise each week
    """
    RedisRollbackExercise().init_candidates_queue()


@register_periodic_task(run_every=crontab(day_of_week="1-5", hour="9-17", minute="*/10"))
def redis_rollback_exercise():
    """
    Generate Redis rollback exercise tasks
    """
    RedisRollbackExercise().start()
