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

from celery import current_app, shared_task
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import PLAT_BIZ_ID, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.constants import CACHE_CLUSTER_STATS
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import (
    CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE,
    CLUSTER_TYPE_LOAD_RULES,
    EXPORTER_UP_QUERY_TEMPLATE,
    QUERY_TEMPLATE,
    SAME_QUERY_TEMPLATE_CLUSTER_TYPE_MAP,
    UNIFY_QUERY_PARAMS,
    RedisLoadStatus,
    TimeUnit,
)
from backend.exceptions import ApiResultError

logger = logging.getLogger("celery")


@shared_task
def update_app_policy(bk_biz_id, notify_group_id, db_type):
    """业务监控策略刷新
    当业务运维配置了业务dba时，可调用该task立即下发策略更新
    notify_group_id: 新建的蓝鲸告警组
    """
    from .models import MonitorPolicy, NoticeGroup

    if not notify_group_id:
        logger.error("update_app_policy skip empty notify_group_id: %s", notify_group_id)
        return

    logger.warning(
        "update_app_policy start bk_biz_id=%s, notify_group_id=%s, db_type=%s", bk_biz_id, notify_group_id, db_type
    )

    # TODO: 批量更新，不太适合自定义策略，告警组很难做聚合
    # policies = MonitorPolicy.get_policies(db_type, bk_biz_id)
    # BKMonitorV3Api.update_partial_strategy_v3({
    #     "ids": policies,
    #     "edit_data": {
    #         "notice_group_list": [
    #             monitor_group_id
    #         ]
    #     },
    #     "bk_biz_id": env.DBA_APP_BK_BIZ_ID
    # })

    if bk_biz_id == PLAT_BIZ_ID:
        logger.error("update_app_policy skip built in policy of %s", bk_biz_id)
        return

    # 逐个策略更新
    for policy in MonitorPolicy.objects.filter(db_type=db_type, bk_biz_id=bk_biz_id):
        plat_groups = NoticeGroup.get_groups(PLAT_BIZ_ID, id_name="id")
        plat_group_id = plat_groups.get(policy.db_type)

        old_notify_groups = copy.deepcopy(policy.notify_groups)

        # 移除平台告警组
        if plat_group_id in policy.notify_groups:
            try:
                policy.notify_groups.remove(plat_group_id)
            except ValueError:
                pass

        # 添加目标告警组
        if notify_group_id not in policy.notify_groups:
            policy.notify_groups.append(notify_group_id)

        if set(policy.notify_groups) != set(old_notify_groups):
            logger.warning(
                "update_app_policy update policy=%s, notify_group_id=%s, db_type=%s: %s -> %s",
                policy.name,
                notify_group_id,
                db_type,
                old_notify_groups,
                policy.notify_groups,
            )
            policy.save()
        else:
            logger.warning(
                "update_app_policy skip policy=%s, notify_group_id=%s, db_type=%s",
                policy.name,
                notify_group_id,
                db_type,
            )


@shared_task
def update_db_notice_group(db_type: str):
    """更新DB类型的告警组"""
    from backend.db_monitor.models import NoticeGroup

    for notice_group in NoticeGroup.objects.filter(is_built_in=True, db_type=db_type):
        logger.info("[local_notice_group] update notice group: %s", notice_group.name)
        notice_group.save()


@shared_task
def delete_monitor_duty_rule(db_type: str, monitor_duty_rule_id):
    """解绑相关告警组，删除轮值策略，调用此函数之前保证轮值已从DBM中删除"""
    update_db_notice_group(db_type)

    logger.info("[duty_rule] delete duty rule: %s", monitor_duty_rule_id)

    try:
        BKMonitorV3Api.delete_duty_rules({"ids": [monitor_duty_rule_id], "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID]})
    except (ApiResultError, Exception) as e:
        # 轮值删除错误暂可忽略，因为删除之前已经停用不会生效，并且在DBM数据也清理。只是会在监控平台留下一条脏数据
        logger.error("[duty_rule] error in deleting duty: %s", e)


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


def query_cap(bk_biz_id, cluster_type, cap_key="used", immute_domains=None):
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
    if immute_domains:
        filters = '{}, cluster_domain=~"{}"'.format(filters, "|".join(c for c in immute_domains))
    params["query_configs"][0]["promql"] = query_template[cap_key] % filters

    series = BKMonitorV3Api.unify_query(params)["series"]

    cluster_bytes = {}
    extra_info = defaultdict(dict)
    for serie in series:
        # 集群：cluster_domain | influxdb: instance_host
        cluster_domain = serie["dimensions"]["cluster_domain"]
        datapoints = list(filter(lambda dp: dp[0] is not None, serie["datapoints"]))

        if not datapoints:
            logger.info("No datapoints for cluster: %s -> %s", cluster_domain, serie["datapoints"])
            continue
        cluster_bytes[cluster_domain] = datapoints[-1][0]
        if cluster_type == ClusterType.TenDBHA.value or cluster_type == ClusterType.TenDBSingle.value:
            extra_info[cluster_domain]["mount_point"] = serie["dimensions"].get("mount_point", "")
            extra_info[cluster_domain]["instance_host"] = serie["dimensions"].get("instance", "").split("-")[0]
    return cluster_bytes, extra_info


def query_cluster_capacity(bk_biz_id, cluster_type):
    """查询集群容量"""

    cluster_cap_bytes = defaultdict(dict)
    domains = list(
        Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
        .values_list("immute_domain", flat=True)
        .distinct()
    )

    used_data, _ = query_cap(bk_biz_id, cluster_type, "used")
    for cluster, used in used_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["used"] = used

    total_data, _ = query_cap(bk_biz_id, cluster_type, "total")
    for cluster, used in total_data.items():
        # 排除无效集群
        if cluster not in domains:
            continue
        cluster_cap_bytes[cluster]["total"] = used

    return cluster_cap_bytes


def query_capacity_for_clusters(bk_biz_id, cluster_type, immute_domains) -> (dict, list):
    """查询指定的集群的容量"""

    if not immute_domains:
        raise Exception("immute_domains parameter is empty")
    cluster_cap_bytes = defaultdict(dict)
    no_stats = []
    used_data, extra_info = query_cap(bk_biz_id, cluster_type, "used", immute_domains)
    total_data, _ = query_cap(bk_biz_id, cluster_type, "total", immute_domains)
    for cluster in immute_domains:
        if cluster in used_data and cluster in total_data and cluster in extra_info:
            cluster_cap_bytes[cluster]["used"] = used_data[cluster]
            cluster_cap_bytes[cluster]["total"] = total_data[cluster]
            cluster_cap_bytes[cluster]["mount_point"] = extra_info[cluster]["mount_point"]
            cluster_cap_bytes[cluster]["host"] = extra_info[cluster]["instance_host"]
            cluster_cap_bytes[cluster]["used_percent"] = "{}%".format(
                round(used_data[cluster] / total_data[cluster] * 100.0, 2)
            )
        else:
            logger.error(
                "No capacity stats for cluster: %s, used: %s, total: %s, mount_point: %s",
                cluster,
                used_data.get(cluster),
                total_data.get(cluster),
                extra_info.get(cluster),
            )
            no_stats.append(cluster)
    return cluster_cap_bytes, no_stats


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
        return {}

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
