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
# server log 日志示例：
# {
#   "bk_biz_id": "111",
#   "bk_cloud_id": 0,
#   "server_ip": "1.1.96.51",
#   "server_port": 50000,
#   "domain": "1.cloud.1.db",
#   "cluster_type": "TwemproxyRedisInstance",
#   "role": "twemproxy",
#   "log_file": "/data/twemproxy-0.2.4/50000/log/twemproxy.50000.log.20260409143757",
#   "data": "[2026-04-10 11:28:34.058] nc_redis.c:3400 authed: 0, r->type:126,...",
#   "time_zone": "CST",
#   "create_time": "2026-04-10T11:28:34+08:00"
# }
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def _parse_serverlog(log_src: Dict) -> Optional[Dict]:
    """解析单条 server log 日志记录"""
    try:
        return {
            "server_ip": log_src.get("server_ip", ""),
            "server_port": log_src.get("server_port", 0),
            "addr": "{}:{}".format(log_src.get("server_ip", ""), log_src.get("server_port", "")),
            "domain": log_src.get("domain", ""),
            "cluster_type": log_src.get("cluster_type", ""),
            "role": log_src.get("role", ""),
            "log_file": log_src.get("log_file", ""),
            "data": log_src.get("data", ""),
            "time_zone": log_src.get("time_zone", ""),
            "create_time": log_src.get("create_time", ""),
        }
    except Exception:
        return None


def _get_serverlog_logs(query_params: Dict) -> List[Dict]:
    """从 BKLog 查询 server log 日志"""
    try:
        resp = BKLogApi.esquery_search(query_params, use_admin=True)
        logs = []
        for hit in resp.get("hits", {}).get("hits", []):
            log_src = hit.get("_source", None)
            if log_src is None:
                continue
            parsed = _parse_serverlog(log_src)
            if parsed:
                logs.append(parsed)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query server logs failed: {e}")
    return logs


def _get_serverlog_query_params(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict:
    """构建 server log 查询参数"""
    query_parts = [f'domain:"{immute_domain}"']
    if host and port:
        query_parts.append(f'server_ip:"{host}"')
        query_parts.append(f'server_port:"{port}"')
    elif host:
        query_parts.append(f'server_ip:"{host}"')

    return {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_server_log",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": " AND ".join(query_parts),
        "start": 0,
        "size": 1000,
        "sort_list": [["dtEventTimeStamp", "desc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }


def get_cluster_serverlog_static(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    """获取集群时间范围内 server log 统计数据"""
    logs = _get_serverlog_logs(_get_serverlog_query_params(immute_domain, start_time, end_time))

    # 按实例维度聚合
    instance_data: Dict[str, Any] = defaultdict(
        lambda: {"total_count": 0, "role": "", "log_files": set(), "latest_logs": []}
    )
    role_count: Dict[str, int] = defaultdict(int)

    for record in logs:
        addr = record.get("addr", "unknown")
        role = record.get("role", "unknown")

        instance_data[addr]["total_count"] += 1
        instance_data[addr]["role"] = role
        instance_data[addr]["log_files"].add(record.get("log_file", ""))
        # 保留最新的 10 条日志
        if len(instance_data[addr]["latest_logs"]) < 10:
            instance_data[addr]["latest_logs"].append(record)

        role_count[role] += 1

    # 构建按实例统计结果
    by_instance = {}
    for addr, data in instance_data.items():
        by_instance[addr] = {
            "total_count": data["total_count"],
            "role": data["role"],
            "log_files": list(data["log_files"]),
            "latest_logs": data["latest_logs"],
        }

    return {
        "summary": {
            "total_count": len(logs),
            "instance_count": len(instance_data),
            "role_distribution": dict(role_count),
        },
        "by_instance": by_instance,
    }


def get_host_or_instance_serverlog(
    immute_domain: str,
    host: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    port: Optional[int] = None,
) -> Dict:
    """获取某台机器或某个实例上时间范围内 server log 日志（port 为空时查询整台机器）"""
    logs = _get_serverlog_logs(_get_serverlog_query_params(immute_domain, start_time, end_time, host=host, port=port))
    return {"total_count": len(logs), "log_entries": logs}
