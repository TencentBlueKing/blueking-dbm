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
from celery import shared_task

from backend.db_periodic_task.constants import PeriodicTaskType
from backend.db_periodic_task.models import DBPeriodicTask

registered_local_tasks = set()


def register_periodic_task(run_every, args=None, kwargs=None):
    """
    注册周期任务
    """

    def inner_wrapper(wrapped_func):
        name = f"{wrapped_func.__module__}.{wrapped_func.__name__}"
        registered_local_tasks.add(name)
        DBPeriodicTask.create_or_update_periodic_task(
            name=name, task=name, task_type=PeriodicTaskType.LOCAL.value, run_every=run_every, args=args, kwargs=kwargs
        )
        return shared_task(wrapped_func)

    return inner_wrapper
