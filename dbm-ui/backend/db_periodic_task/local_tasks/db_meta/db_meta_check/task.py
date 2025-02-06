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

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_report.models import MetaCheckReport

from .check_redis_instance import check_redis_instance
from .mysql_cluster_topo import tendbcluster, tendbha
from .sqlserver_cluster_topo.check import sqlserver_dbmeta_check

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=3, hour=2))
def db_meta_check_task():
    """
    巡检校验元数据
    """
    check_redis_instance()


@register_periodic_task(run_every=crontab(hour=2, minute=30))
def tendbha_topo_daily_check():
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA):
        r: MetaCheckReport
        for r in tendbha.health_check(c.id):
            r.save()


@register_periodic_task(run_every=crontab(hour=2, minute=30))
def tendbcluster_topo_daily_check():
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster):
        r: MetaCheckReport
        for r in tendbcluster.health_check(c.id):
            r.save()


@register_periodic_task(run_every=crontab(hour=5, minute=30))
def sqlserver_topo_daily_check():
    # 只检查online状态的集群
    for c in Cluster.objects.filter(
        phase=ClusterPhase.ONLINE, cluster_type__in=[ClusterType.SqlserverHA, ClusterType.SqlserverSingle]
    ):
        r: MetaCheckReport
        for r in sqlserver_dbmeta_check(c.id):
            r.save()
