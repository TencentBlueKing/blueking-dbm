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

from backend.db_periodic_task.local_tasks.redis_tasks.check_cluster_memory_growth import CheckClusterMemoryGrowthTask
from backend.db_periodic_task.local_tasks.redis_tasks.check_exporter import CheckRedisUpMetricTask
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_report.repo.task_record_repo import TaskRecordRepo

"""
    register_periodic_task 注册新的周期任务注意
    1. 通过装饰器注册周期任务
    2. import到 ../__init__.py
"""


@register_periodic_task(run_every=crontab(minute="*/10"))
def redis_cluster_memory_growth_check_task():
    """Redis cluster memory growth check (LLM agent). Runs every 10 minutes."""
    CheckClusterMemoryGrowthTask().start()


@register_periodic_task(run_every=crontab(minute=1, hour=8))
def redis_exporter_check_task():
    """
    redis exporter巡检任务

    检查项包括:
    1. redis_exporter_down: redis_exporter的up指标值为0, 则认为异常
    2. redis_exporter_duplicate: 重复的节点. 本集群的节点上报了相同的指标
    3. redis_exporter_redundant: 多余的节点. 存在集群外的节点上报本集群的指标
    4. redis_exporter_redundant2: 多余的metric. 本集群的节点上报了其他集群的指标
    5. proxy_exporter_down: proxy_exporter的up指标值为0, 则认为异常
    6. proxy_exporter_duplicate: 重复的proxy节点. 本集群的proxy节点上报了相同的指标
    7. proxy_exporter_redundant: 多余的proxy节点. 存在集群外的proxy节点上报本集群的指标
    8. proxy_exporter_redundant2: 多余的metric. 本集群的proxy节点上报了其他集群的指标
    """
    repo = TaskRecordRepo()
    repo.execute_task_with_record(
        db_type="redis",
        task_name="redis_exporter_check_task",
        task_type="exporter",
        check_task_instance=CheckRedisUpMetricTask(),
    )
