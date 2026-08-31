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
from backend.db_periodic_task.local_tasks.doris.sync_cluster_master import sync_cluster_master
from backend.db_periodic_task.local_tasks.doris.sync_cluster_remote_used import sync_cluster_remote_used

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour="*/1", minute=0))
def doris_sync_master_task():
    """
    Doris 同步master节点 定时任务
    按业务从监控API同步各个Doris集群的master节点
    @:return: None
    """

    logger.info("start doris sync master node task")
    biz_ids = (
        Cluster.objects.filter(cluster_type=ClusterType.Doris.value).values_list("bk_biz_id", flat=True).distinct()
    )
    # 不同业务的同步master节点任务
    for biz_id in biz_ids:
        sync_cluster_master.apply_async(args=(biz_id,))


@register_periodic_task(run_every=crontab(hour="*/1", minute=0))
def doris_sync_remote_used_task():
    """
    Doris 同步远程存储用量 定时任务
    按业务从监控API同步各个Doris集群的远程存储用量
    @:return: None
    """

    logger.info("start doris sync remote used task")
    biz_ids = (
        Cluster.objects.filter(cluster_type=ClusterType.Doris.value).values_list("bk_biz_id", flat=True).distinct()
    )
    # 不同业务的同步远程存储用量任务
    for biz_id in biz_ids:
        sync_cluster_remote_used.apply_async(args=(biz_id,))
