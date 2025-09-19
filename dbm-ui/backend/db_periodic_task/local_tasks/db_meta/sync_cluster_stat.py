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
import time
from collections import defaultdict

from celery import current_app
from celery.schedules import crontab
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.constants import CACHE_CLUSTER_STATS
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task, start_new_span
from backend.db_periodic_task.local_tasks.db_meta.constants import (
    CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE,
    CLUSTER_TYPE_LOAD_RULES,
    EXPORTER_UP_QUERY_TEMPLATE,
    QUERY_TEMPLATE,
    SAME_QUERY_TEMPLATE_CLUSTER_TYPE_MAP,
    UNIFY_QUERY_PARAMS,
    RedisLoadStatus,
)
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("celery")


def query_cluster_exporter_up(db_type, exporter):
    """查询某类集群的 exporter 是否正常"""
    # 获取查询模板
    query_template = EXPORTER_UP_QUERY_TEMPLATE.get(db_type)
    if not query_template:
        logger.error("No query template for cluster type: %s and exporter: %s", db_type, exporter)
        return {}

    # 查询业务固定为DBA，查询时间取模板range
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["end_time"] = int(time.time())
    params["start_time"] = params["end_time"] - int(query_template["range"]) * 60
    params["query_configs"][0]["promql"] = query_template[exporter]

    # 查询exporter up指标
    series = BKMonitorV3Api.unify_query(params)["series"]
    cluster_exporter_up_map = {
        data["dimensions"]["cluster_domain"]: data["datapoints"][0][0] for data in series if data["datapoints"]
    }
    return cluster_exporter_up_map


def query_cap(bk_biz_id, cluster_type, cap_key="used", clusters=None):
    """查询某类集群的某种容量: used/total"""

    cluster_type = SAME_QUERY_TEMPLATE_CLUSTER_TYPE_MAP.get(cluster_type, cluster_type)
    query_template = QUERY_TEMPLATE.get(cluster_type)
    if not query_template:
        logger.error("No query template for cluster type: %s", cluster_type)
        return {}

    # now-5/15m ~ now
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=query_template["range"])

    params = copy.deepcopy(UNIFY_QUERY_PARAMS)

    # mysql 的指标不连续，使用 "type": "instant" 会导致查询结果为空
    if cluster_type in [ClusterType.TenDBSingle.value, ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value]:
        params.pop("type", "")

    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    filters = 'appid="{}"'.format(bk_biz_id)

    # 获取指定域名的指标数据
    if clusters:
        filters = '{}, cluster_domain=~"{}"'.format(filters, "|".join(c for c in clusters))
    params["query_configs"][0]["promql"] = query_template[cap_key] % filters
    series = BKMonitorV3Api.unify_query(params)["series"]

    cluster_bytes = {}
    for serie in series:
        # 集群：cluster_domain | influxdb: instance_host
        cluster_domain = list(serie["dimensions"].values())[0]
        datapoints = list(filter(lambda dp: dp[0] is not None, serie["datapoints"]))

        if not datapoints:
            logger.info("No datapoints for cluster: %s -> %s", cluster_domain, serie["datapoints"])
            continue
        cluster_bytes[cluster_domain] = datapoints[-1][0]

    return cluster_bytes


def query_cluster_capacity(bk_biz_id, cluster_type):
    """查询集群容量"""

    cluster_cap_bytes = defaultdict(dict)
    domains = list(
        Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
        .values_list("immute_domain", flat=True)
        .distinct()
    )

    used_data = query_cap(bk_biz_id, cluster_type, "used")
    for cluster, used in used_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["used"] = used

    total_data = query_cap(bk_biz_id, cluster_type, "total")
    for cluster, used in total_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["total"] = used

    return cluster_cap_bytes


def query_capacity_for_clusters(bk_biz_id, cluster_type, clusters) -> dict:
    """查询指定的集群的容量"""

    if not clusters:
        raise Exception(_("参数clusters不应该为空"))
    cluster_cap_bytes = defaultdict(dict)
    no_stats = []
    used_data = query_cap(bk_biz_id, cluster_type, "used", clusters)
    total_data = query_cap(bk_biz_id, cluster_type, "total", clusters)
    for cluster in clusters:
        if cluster in used_data and cluster in total_data:
            cluster_cap_bytes[cluster]["used"] = used_data[cluster]
            cluster_cap_bytes[cluster]["total"] = total_data[cluster]
        else:
            no_stats.append(cluster)
    if no_stats:
        raise Exception(_("没有[{}]集群的统计信息").format(no_stats))
    return cluster_cap_bytes


def query_cluster_load(cluster_type, clusters) -> (dict, dict):
    """查询集群负载"""

    if cluster_type not in CLUSTER_TYPE_LOAD_RULES:
        raise Exception(_("暂不支持该集群类型的查询: {}").format(cluster_type))

    if not clusters:
        return {}, {}

    common_params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    common_params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    # 默认查询前后1h的数据
    now = datetime.datetime.now(timezone.utc)
    common_params["end_time"] = int(now.timestamp())
    common_params["start_time"] = int((now - datetime.timedelta(minutes=60)).timestamp())

    # 初始化cluster负载数据结构
    load_tpl_map = defaultdict(dict)
    for machine in CLUSTER_TYPE_LOAD_RULES[cluster_type]:
        load_tpl_map[machine].update({index: {} for index in CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE[machine]})
    cluster_load_map = defaultdict(lambda: copy.deepcopy(load_tpl_map))

    cluster_load_rule = SystemSettings.get_setting_value(SystemSettingsEnum.CLUSTER_LOAD_RULE, default={})
    # 批量查询集群负载指标
    for machine in CLUSTER_TYPE_LOAD_RULES[cluster_type]:
        machine_threshold = cluster_load_rule.get(machine, {})
        for target, check in CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE[machine].items():
            target_threshold = machine_threshold.get(target, {})

            params = copy.deepcopy(common_params)
            params["query_configs"][0]["promql"] = check["promql"].replace("{cluster_domains}", "|".join(clusters))
            series = BKMonitorV3Api.unify_query(params)["series"]
            # 解析时序数据，默认取第一个数据节点
            for data in series:
                cluster_domain = data["dimensions"].pop("cluster_domain")
                target_value = list(data["dimensions"].values())[0]

                data_point = data["datapoints"][0][0] if data["datapoints"] else None
                if not data_point:
                    continue

                # 更新负载数据
                cluster_load_map[cluster_domain][machine][target].update({target_value: data_point})
                # 更新负载状态
                if data_point > target_threshold.get("max", check["max"]):
                    cluster_load_map[cluster_domain][machine][target].update(status=RedisLoadStatus.HIGH.value)
                elif data_point < target_threshold.get("min", check["min"]):
                    cluster_load_map[cluster_domain][machine][target].update(status=RedisLoadStatus.LOW.value)
                else:
                    cluster_load_map[cluster_domain][machine][target].update(status="")

    def __update_cluster_load(data_map, loads):
        status_list = list(set([load["status"] for load in loads.values() if "status" in load]))
        # 任意一个组件有高负载则定义为高负载，所有组件都处于低负载则定义为低负载
        if RedisLoadStatus.HIGH.value in status_list:
            data_map.update(status=RedisLoadStatus.HIGH.value)
        elif len(status_list) == 1 and status_list[0] == RedisLoadStatus.LOW.value:
            data_map.update(status=RedisLoadStatus.LOW.value)
        else:
            data_map.update(status="")

    # 汇总 machine 维度负载状态
    load_status_map = defaultdict(lambda: {m: {} for m in CLUSTER_TYPE_LOAD_RULES[cluster_type]})
    for cluster_domain, machine_loads in cluster_load_map.items():
        for machine, loads in machine_loads.items():
            __update_cluster_load(load_status_map[cluster_domain][machine], loads)
        __update_cluster_load(load_status_map[cluster_domain], load_status_map[cluster_domain])

    return load_status_map, cluster_load_map


def sync_cluster_load_by_cluster_type(bk_biz_id, cluster_type):
    """
    按集群类型同步各集群负载状态
    """
    cluster_domains = list(
        Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
        .values_list("immute_domain", flat=True)
        .distinct()
    )
    # TODO: 是否需要cache?
    return query_cluster_load(cluster_type, cluster_domains)


@current_app.task
def sync_cluster_stat_by_cluster_type(bk_biz_id, cluster_type):
    """
    按集群类型同步各集群容量状态
    """

    logger.info("sync_cluster_stat_from_monitor started")
    try:
        cluster_stats = query_cluster_capacity(bk_biz_id, cluster_type)
    except Exception as e:
        logger.error("query_cluster_capacity error: %s -> %s", cluster_type, e)
        return

    # 计算使用率
    for cluster, cap in cluster_stats.items():
        # 兼容查不到数据的情况
        if not ("used" in cap and "total" in cap):
            continue
        cap["in_use"] = round(cap["used"] * 100.0 / cap["total"], 2)

    cache.set(
        f"{CACHE_CLUSTER_STATS}_{bk_biz_id}_{cluster_type}", json.dumps(cluster_stats), timeout=2 * TimeUnit.HOUR
    )

    return cluster_stats


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
