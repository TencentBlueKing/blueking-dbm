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

from backend.db_meta.models import Cluster
from backend.db_monitor.tasks import sync_cluster_stat_by_cluster_type
from backend.db_periodic_task.local_tasks import register_periodic_task, start_new_span
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour="*/1", minute=0))
def sync_cluster_stat_from_monitor():
    """
    同步各集群容量状态
    """

    logger.info("sync_cluster_stat_from_monitor started")
    biz_cluster_types = Cluster.objects.values_list("bk_biz_id", "cluster_type").distinct()

    count = len(biz_cluster_types)
    for index, (bk_biz_id, cluster_type) in enumerate(biz_cluster_types):
        countdown = calculate_countdown(count=count, index=index, duration=1 * TimeUnit.HOUR)
        logger.info(
            "{}_{} sync_cluster_stat_from_monitor will be run after {} seconds.".format(
                bk_biz_id, cluster_type, countdown
            )
        )
        with start_new_span(sync_cluster_stat_by_cluster_type):
            sync_cluster_stat_by_cluster_type.apply_async(
                kwargs={"bk_biz_id": bk_biz_id, "cluster_type": cluster_type}, countdown=countdown
            )
