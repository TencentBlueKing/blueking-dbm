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
import json

from celery import shared_task
from django_celery_beat.models import PeriodicTask
from django_celery_beat.schedulers import ModelEntry

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
        # 转换执行周期
        model_schedule, model_field = ModelEntry.to_model_schedule(run_every)
        # 转换执行参数
        _args = json.dumps(args or [])
        _kwargs = json.dumps(kwargs or {})

        try:
            db_task = DBPeriodicTask.objects.get(name=name)
        except DBPeriodicTask.DoesNotExist:
            # 新建周期任务
            celery_task = PeriodicTask.objects.create(
                name=name, task=name, args=_args, kwargs=_kwargs, **{model_field: model_schedule}
            )
            DBPeriodicTask.objects.create(name=name, task=celery_task, task_type=PeriodicTaskType.LOCAL.value)
        else:
            # 未冻结的情况，需要更新执行周期和执行参数
            if not db_task.is_frozen:
                celery_task = db_task.task
                setattr(celery_task, model_field, model_schedule)
                celery_task.args = _args
                celery_task.kwargs = _kwargs
                celery_task.save(update_fields=[model_field, "args", "kwargs"])

        return shared_task(wrapped_func)

    return inner_wrapper
