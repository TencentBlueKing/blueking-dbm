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

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.local_tasks.doris.monitor import query_promql
from backend.db_periodic_task.local_tasks.hdfs.constants import MONITOR_QUERY_HDFS_TEMPLATE, MonitorQueryType
from backend.db_periodic_task.utils import TimeUnit
from backend.flow.utils.hdfs.consts import CACHE_CLUSTER_MASTER

logger = logging.getLogger("celery")


@app.task
def sync_cluster_master(bk_biz_id: int):
    """
    按业务同步 HDFS 集群 Active NameNode 到 Cache
    对齐 doris.sync_cluster_master 的实现，方便复用消费端逻辑
    """
    cluster_type = ClusterType.Hdfs.value
    logger.info("hdfs sync cluster master started, bk_biz_id=%s", bk_biz_id)
    try:
        cluster_master_stats = query_cluster_master_by_monitor(bk_biz_id)
    except Exception:
        logger.exception("query_cluster_master_by_monitor error, bk_biz_id=%s", bk_biz_id)
        return

    cache.set(
        f"{CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type}",
        json.dumps(cluster_master_stats),
        timeout=2 * TimeUnit.HOUR,
    )
    logger.info("hdfs sync cluster master finished, bk_biz_id=%s, size=%s", bk_biz_id, len(cluster_master_stats))


def query_cluster_master_by_monitor(bk_biz_id, clusters=None):
    """
    调用监控 API 查询 HDFS 集群 active namenode

    Args:
        bk_biz_id: 业务ID
        clusters: 集群 immute_domain 列表，为空则查全业务

    Returns:
        dict: {cluster_domain: instance_host}，只包含 State=1(active) 的 NN
    """

    # PromQL 查询：5 分钟窗口内最后一次采样值为 1 即 active NN
    result = query_promql(MONITOR_QUERY_HDFS_TEMPLATE, MonitorQueryType.MASTER.value, bk_biz_id, clusters)

    cluster_master_map = {}
    for row in result:
        cluster_domain = list(row["dimensions"].values())[0]
        instance = list(row["dimensions"].values())[1]
        cluster_master_map[cluster_domain] = instance.replace("-", ":")

    return cluster_master_map
