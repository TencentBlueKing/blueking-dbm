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
import logging
from datetime import datetime, timedelta

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import PromQLQueryBuilder, execute_promql
from backend.dbm_aiagent.mcp_tools.mysql.constants import METRIC_TYPES

logger = logging.getLogger("celery.mysql_skew_detect.calculate_skew_data.fetch_metrics")


def _fetch_metric_of_cluster_instances(
    cluster_type: ClusterType,
    cluster_domains: list[str],
    metric_name: str,
    end_time: datetime,
    time_window_len: timedelta = timedelta(minutes=5),
) -> list[dict]:
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    start_time_str = (end_time - time_window_len).strftime("%Y-%m-%d %H:%M:%S")

    promql_tmpl = METRIC_TYPES[metric_name]
    query_builder = promql_tmpl.get(cluster_type) or promql_tmpl.get("default")
    # deep copy 避免污染全局模板
    query_builder = copy.deepcopy(query_builder)

    query_builder.group_by += ["bk_target_ip", "cluster_domain"]
    query_builder.start_time = start_time_str
    query_builder.end_time = end_time_str

    domains_match_filter = "|".join(cluster_domains)
    res = []
    try:
        result = _query_promql_metrics_with_roles(domains_match_filter, [], query_builder)

        for s in result["series"]:
            res.append(
                {
                    "cluster_domain": s["dimensions"]["cluster_domain"],
                    "ip": s["dimensions"]["bk_target_ip"],
                    "port": s["dimensions"].get("instance", "0-0").split("-")[1],
                    "role": s["dimensions"]["instance_role"],
                    "avg": s["stat"]["avg"][1],
                }
            )
    except Exception:  # noqa
        logger.exception("query %s metrics failed", domains_match_filter)

    return res


def _fetch_key_metrics_of_cluster_instances(
    cluster_type: ClusterType,
    cluster_domains: list[str],
    end_time: datetime,
    time_window_len: timedelta = timedelta(minutes=5),
) -> dict[str, list[dict]]:
    res = {}
    for metric_name in ["cpu_summary", "qps_summary", "connections", "memory_usage", "disk_used"]:
        metric_res = _fetch_metric_of_cluster_instances(
            cluster_type=cluster_type,
            cluster_domains=cluster_domains,
            metric_name=metric_name,
            end_time=end_time,
            time_window_len=time_window_len,
        )
        res[metric_name] = metric_res

    return res


def _query_promql_metrics_with_roles(
    cluster_domain_pattern: str, instance_roles: list[str], p: PromQLQueryBuilder
) -> dict:
    if not p.filters or not p.group_by:
        raise Exception("filters or group_by in {} is None".format(p))

    p.filters.append({"label_name": "cluster_domain", "op": "match", "value": cluster_domain_pattern})
    if "cluster_domain" not in p.group_by:
        p.group_by.append("cluster_domain")

    if instance_roles:
        p.filters.append({"label_name": "instance_role", "op": "match", "value": "|".join(instance_roles)})
        if "instance_role" not in p.group_by:
            p.group_by.append("instance_role")

    promql_dict = p.prepare_promql()
    expr = promql_dict.pop("expression", None)
    return execute_promql(
        prom_queries=promql_dict, expr=expr, start_time=p.start_time, end_time=p.end_time, step=p.step
    )
