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
import threading

from celery.schedules import crontab

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_cluster_skew.calculate_skew_data.skew_detect import (
    _calculate_mysql_skew,
)

logger = logging.getLogger("celery.mysql_cluster_skew.calculate_skew_data.task")

calculate_tendbha_skew_lock = threading.Lock()
calculate_tendbcluster_skew_lock = threading.Lock()


@register_periodic_task(run_every=crontab(minute="*/5"))
def calculate_tendbha_skew():
    if calculate_tendbha_skew_lock.acquire(blocking=False):
        try:
            _calculate_mysql_skew(cluster_type=ClusterType.TenDBHA, pool_size=10, batch_size=20)
        except Exception:  # noqa
            logger.exception("calculate tendbha skew failed")
        finally:
            calculate_tendbha_skew_lock.release()
    else:
        logger.warning("tendbha lock not acquired")


@register_periodic_task(run_every=crontab(minute="*/5"))
def calculate_tendbcluster_skew():
    if calculate_tendbcluster_skew_lock.acquire(blocking=False):
        try:
            _calculate_mysql_skew(cluster_type=ClusterType.TenDBCluster, pool_size=10, batch_size=5)
        except Exception:  # noqa
            logger.exception("calculate tendbcluster skew failed")
        finally:
            calculate_tendbcluster_skew_lock.release()
    else:
        logger.warning("tendbcluster lock not acquired")
