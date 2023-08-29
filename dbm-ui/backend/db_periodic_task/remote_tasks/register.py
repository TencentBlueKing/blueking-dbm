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

from backend.components.base import DataAPI
from backend.components.celery_service.client import CeleryServiceApi
from backend.db_periodic_task.constants import (
    MAX_QUERY_TASK_STATUS_TIMES,
    QUERY_TASK_STATUS_INTERVAL,
    PeriodicTaskType,
)
from backend.db_periodic_task.models import DBPeriodicTask
from backend.env import CELERY_SERVICE_APIGW_DOMAIN

logger = logging.getLogger("root")
registered_remote_tasks = set()


def register_from_remote():
    """
    从远端 API 注册周期任务
    """
    async_task_list = CeleryServiceApi.list()
    remote_task_name = f"{remote_call.__module__}.{remote_call.__name__}"
    for task_info in async_task_list:
        registered_remote_tasks.add(task_info["path"])
        DBPeriodicTask.create_or_update_periodic_task(
            name=task_info["path"],
            task=remote_task_name,
            task_type=PeriodicTaskType.REMOTE.value,
            run_every=crontab(**task_info["crontab"]),
            args=[task_info],
        )


@shared_task
def remote_call(async_task_info):
    """
    远程调用注册的 API，并轮询执行状态
    """
    method, path = async_task_info["method"], async_task_info["path"]
    celery_method_name = path.replace("/", "_")
    if not hasattr(CeleryServiceApi, path):
        setattr(
            CeleryServiceApi,
            path,
            DataAPI(
                method=celery_method_name,
                base=CELERY_SERVICE_APIGW_DOMAIN,
                url=path,
                module=CeleryServiceApi.MODULE,
                description=f"Dynamic Periodic Interface--{path}",
            ),
        )

    # TODO: 考虑请求参数如何填充
    session_id = getattr(CeleryServiceApi, celery_method_name)()
    query_async_task_status(session_id, 1)


@shared_task
def query_async_task_status(session_id, query_times):
    """
    周期性轮询任务执行状态
    """
    if query_times > MAX_QUERY_TASK_STATUS_TIMES:
        logger.error(f"The current number of polls exceeds the limit {MAX_QUERY_TASK_STATUS_TIMES}")
        return

    task_exc_data = CeleryServiceApi.async_query({"session_id": session_id})[0]
    if task_exc_data["done"]:
        # TODO: 考虑如何记录任务执行日志
        logger.info(task_exc_data)
        return

    query_async_task_status.apply_async((session_id, query_times + 1), countdown=QUERY_TASK_STATUS_INTERVAL)
