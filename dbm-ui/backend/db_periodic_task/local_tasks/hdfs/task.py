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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.hdfs.sync_cluster_master import sync_cluster_master

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour="*/1", minute="10"))
def hdfs_sync_master_task():
    """
    HDFS 同步 Active NameNode 定时任务
    按业务从监控 API 同步各个 HDFS 集群的 active namenode 到 Cache
    """
    logger.info("start hdfs sync master node task")
    biz_ids = (
        Cluster.objects.filter(cluster_type=ClusterType.Hdfs.value).values_list("bk_biz_id", flat=True).distinct()
    )
    for biz_id in biz_ids:
        sync_cluster_master.apply_async(args=(biz_id,))
