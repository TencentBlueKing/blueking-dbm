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
import copy
import datetime
import json
import logging
from collections import defaultdict

from celery.schedules import crontab
from celery.task import task
from django.core.cache import cache
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.constants import CACHE_CLUSTER_STATS
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance

from ..register import register_periodic_task
from .constants import QUERY_TEMPLATE, UNIFY_QUERY_PARAMS

logger = logging.getLogger("celery")


def query_cap(cluster_type, cap_key="used"):
    """查询某类集群的某种容量: used/total"""

    query_template = QUERY_TEMPLATE.get(cluster_type)
    if not query_template:
        logger.error("No query template for cluster type: %s", cluster_type)
        return {}

    # now-5/15m ~ now
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=query_template["range"])

    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    # 加速查询
    params["type"] = "instant"

    params["query_configs"][0]["promql"] = query_template[cap_key]
    series = BKMonitorV3Api.unify_query(params)["series"]

    # print(cluster_type, cap_key, json.dumps(params, indent=2), json.dumps(series, indent=2))

    cluster_bytes = {}
    for serie in series:
        # 集群：cluster_domain | influxdb: instance_host
        cluster_domain = list(serie["dimensions"].values())[0]
        # cluster_domain = serie["dimensions"]["cluster_domain"]
        datapoints = list(filter(lambda dp: dp[0] is not None, serie["datapoints"]))

        if not datapoints:
            logger.info("No datapoints for cluster: %s -> %s", cluster_domain, serie["datapoints"])
            continue
        cluster_bytes[cluster_domain] = datapoints[-1][0]

    return cluster_bytes


def query_cluster_capacity(cluster_type):
    """查询集群容量"""

    cluster_cap_bytes = defaultdict(dict)

    domains = (
        list(Cluster.objects.filter(cluster_type=cluster_type).values_list("immute_domain", flat=True).distinct())
        if cluster_type != ClusterType.Influxdb
        else StorageInstance.objects.filter(instance_role=InstanceRole.INFLUXDB).values_list("machine__ip", flat=True)
    )

    used_data = query_cap(cluster_type, "used")
    for cluster, used in used_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["used"] = used

    total_data = query_cap(cluster_type, "total")
    for cluster, used in total_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["total"] = used

    # print(cluster_type, cluster_cap_bytes)
    return cluster_cap_bytes


@task
def sync_cluster_stat_by_cluster_type(cluster_type):
    """
    按集群类型同步各集群容量状态
    """

    logger.info("sync_cluster_stat_from_monitor started")
    cluster_types = list(Cluster.objects.values_list("cluster_type", flat=True).distinct())
    cluster_types.append(ClusterType.Influxdb.value)

    cluster_stats = {}
    try:
        cluster_capacity = query_cluster_capacity(cluster_type)
        cluster_stats.update(cluster_capacity)
    except Exception as e:
        logger.error("query_cluster_capacity error: %s -> %s", cluster_type, e)

    # 计算使用率
    for cluster, cap in cluster_stats.items():
        # 兼容查不到数据的情况
        if not ("used" in cap and "total" in cap):
            continue
        cap["in_use"] = round(cap["used"] * 100.0 / cap["total"], 2)

    # print(cluster_stats)
    cache.set(f"{CACHE_CLUSTER_STATS}_{cluster_type}", json.dumps(cluster_stats))


@register_periodic_task(run_every=crontab(minute="*/3"))
def sync_cluster_stat_from_monitor():
    """
    同步各集群容量状态
    """

    logger.info("sync_cluster_stat_from_monitor started")
    cluster_types = list(Cluster.objects.values_list("cluster_type", flat=True).distinct())
    cluster_types.append(ClusterType.Influxdb.value)

    for cluster_type in cluster_types:
        sync_cluster_stat_by_cluster_type.apply_async(args=[cluster_type])
