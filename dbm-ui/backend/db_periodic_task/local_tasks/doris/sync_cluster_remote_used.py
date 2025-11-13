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
import logging

from blueapps.core.celery.celery import app
from django.core.cache import cache

from backend.db_periodic_task.local_tasks.doris.constants import MONITOR_QUERY_DORIS_TEMPLATE, MonitorQueryType
from backend.db_periodic_task.local_tasks.doris.monitor import query_promql
from backend.db_periodic_task.utils import TimeUnit
from backend.flow.utils.doris.consts import CACHE_DORIS_REMOTE_USED

logger = logging.getLogger("celery")


@app.task
def sync_cluster_remote_used(bk_biz_id: int):
    logger.info("doris sync cluster remote used started")
    try:
        cluster_stats = query_cluster_remote_used(bk_biz_id)
    except Exception as e:
        logger.error("query_cluster_remote_used error: %d -> %s", bk_biz_id, e)
        return

    cache.set(f"{CACHE_DORIS_REMOTE_USED}_{bk_biz_id}", json.dumps(cluster_stats), timeout=2 * TimeUnit.HOUR)


def query_cluster_remote_used(bk_biz_id, clusters=None):
    """
    调用监控API查询集群远程存储数据使用量
    :param bk_biz_id:
    :param clusters:
    :return:
    """

    result = query_promql(MONITOR_QUERY_DORIS_TEMPLATE, MonitorQueryType.REMOTE_USED.value, bk_biz_id, clusters)

    cluster_remote_used_stats = {}
    for row in result:
        cluster_domain = list(row["dimensions"].values())[0]
        datapoints = list(filter(lambda dp: dp[0] is not None, row["datapoints"]))
        cluster_remote_used_stats[cluster_domain] = datapoints[-1][0]

    return cluster_remote_used_stats
