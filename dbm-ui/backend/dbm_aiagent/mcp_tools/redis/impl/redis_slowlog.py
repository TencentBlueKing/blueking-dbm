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
import statistics
from collections import defaultdict
from typing import Any, Dict, List

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster, Machine
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def _calc_duration_stats(durations: List[int]) -> Dict[str, Any]:
    """内部函数：计算耗时统计信息"""
    if not durations:
        return {
            # "max_us": 0, "min_us": 0, "avg_us": 0, "median_us": 0,
            "max_ms": 0,
            "min_ms": 0,
            "avg_ms": 0,
            "median_ms": 0,
            "std_dev_us": 0,
        }

    max_dur = max(durations)
    min_dur = min(durations)
    avg_dur = statistics.mean(durations)
    median_dur = statistics.median(durations)

    return {
        # "max_us": max_dur,
        # "min_us": min_dur,
        # "avg_us": round(avg_dur, 2),
        # "median_us": median_dur,
        "max_ms": round(max_dur / 1000, 2),
        "min_ms": round(min_dur / 1000, 2),
        "avg_ms": round(avg_dur / 1000, 2),
        "median_ms": round(median_dur / 1000, 2),
        # "std_dev_us": round(std_dev, 2)
    }


def get_cluster_slowlog_static(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> List[Dict]:
    cluster_slows = []
    proxies_slowlogs = _get_slowlog(
        get_query_params(immute_domain=immute_domain, role="proxy", start_time=start_time, end_time=end_time)
    )
    master_slowlogs = _get_slowlog(
        get_query_params(immute_domain=immute_domain, role="redis_master", start_time=start_time, end_time=end_time)
    )
    cluster_slows.extend(proxies_slowlogs)
    cluster_slows.extend(master_slowlogs)

    # 按实例维度聚合数据
    instance_data = defaultdict(lambda: {"durations": [], "commands": defaultdict(int), "keys": [], "records": []})

    all_durations = []
    all_commands = defaultdict(int)

    # 遍历数据进行聚合
    for record in cluster_slows:
        instance = record.get("instance_addr", "unknown")
        duration = record.get("duration_us", 0)
        cmd = record.get("cmd", "unknown")
        key = record.get("key", "")

        instance_data[instance]["durations"].append(duration)
        instance_data[instance]["commands"][cmd] += 1
        instance_data[instance]["keys"].append(key)
        instance_data[instance]["records"].append(record)

        all_durations.append(duration)
        all_commands[cmd] += 1

    # 计算统计结果
    result = {
        "summary": {
            "total_count": len(cluster_slows),
            "instance_count": len(instance_data),
            "duration_stats": _calc_duration_stats(all_durations),
            # "command_stats": dict(all_commands),
            "top_commands": dict(sorted(all_commands.items(), key=lambda x: x[1], reverse=True)[:10]),
        },
        "by_instance": {},
    }

    # 按实例计算统计信息
    for instance, data in instance_data.items():
        durations = data["durations"]
        commands = data["commands"]
        records = data["records"]

        # 获取最慢查询
        slowest = max(records, key=lambda x: x.get("duration_us", 0)) if records else {}
        slowest_info = (
            {
                "cmd": slowest.get("cmd", "unknown"),
                "key": slowest.get("key", ""),
                # "duration_us": slowest.get('duration_us', 0),
                "duration_ms": round(slowest.get("duration_us", 0) / 1000, 2),
                "create_time": slowest.get("create_time", ""),
                # "id": slowest.get('id', '')
            }
            if slowest
            else {}
        )

        result["by_instance"][instance] = {
            "total_count": len(durations),
            "duration_stats": _calc_duration_stats(durations),
            # "command_stats": dict(commands),
            "top_commands": dict(sorted(commands.items(), key=lambda x: x[1], reverse=True)[:5]),
            # "unique_keys": len(set(data["keys"])),
            "slowest_query": slowest_info,
        }
    return result


def get_host_slowlog(
    host: str,
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> List[Dict]:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
    machine_obj = Machine.objects.get(bk_cloud_id=cluster_obj.bk_cloud_id, ip=host)

    host_slows = []
    if machine_obj.access_layer == AccessLayer.PROXY.value:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain, role="proxy", start_time=start_time, end_time=end_time, host=host
            )
        )
    else:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain, role="redis_master", start_time=start_time, end_time=end_time, host=host
            )
        )

    return {"slowlog_entries": host_slows, "total_count": len(host_slows)}


def get_instance_slowlog(
    host: str,
    port: int,
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> List[Dict]:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
    machine_obj = Machine.objects.get(bk_cloud_id=cluster_obj.bk_cloud_id, ip=host)

    host_slows = []
    if machine_obj.access_layer == AccessLayer.PROXY.value:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain,
                role="proxy",
                start_time=start_time,
                end_time=end_time,
                host=host,
                port=port,
            )
        )
    else:
        host_slows = _get_slowlog(
            get_query_params(
                immute_domain=immute_domain,
                role="redis_master",
                start_time=start_time,
                end_time=end_time,
                host=host,
                port=port,
            )
        )

    return {"slowlog_entries": host_slows, "total_count": len(host_slows)}


def _get_slowlog(
    query_params: Dict,
) -> Dict:
    try:
        resp = BKLogApi.esquery_search(
            query_params,
            use_admin=True,
        )

        slog_logs = []
        for hit in resp["hits"]["hits"]:
            log_src = hit.get("_source", None)
            if log_src is None:
                continue
            slow_query = log_src.get("redis", None)
            if slow_query is None:
                continue
            slowlog_d = slow_query.get("slowlog", "")
            slowlog_d["instance_addr"] = "{}:{}".format(
                log_src["__ext"]["instance_host"], log_src["__ext"]["instance_port"]
            )
            slowlog_d["instance_role"] = log_src["__ext"]["instance_role"]
            slowlog_d["create_time"] = log_src["event"]["created"]
            slowlog_d["duration_us"] = slowlog_d["duration"]["us"]
            slog_logs.append(slowlog_d)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query slow logs failed: {e}")

    return slog_logs


def get_query_params(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    role=None,
    host=None,
    port=None,
) -> Dict:

    query_parts = [f'__ext.cluster_domain:"{immute_domain}"']
    if role:
        query_parts.append(f'__ext.instance_role:"{role}"')
    if host:
        query_parts.append(f'__ext.instance_host:"{host}"')
    if port:
        query_parts.append(f'__ext.instance_port:"{port}"')

    query_params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_slowlog",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": " AND ".join(query_parts),
        "start": 0,
        "size": 1000,
        "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }

    return query_params
