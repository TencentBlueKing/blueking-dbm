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
# 大key日志示例：
# {
#   "app": "11",
#   "addr": "1.4.202.34:30016",
#   "domain": "s.mobile.333.db",
#   "@timestamp": "2026-04-10T11:21:37+08:00",
#   "top_idx": 2,
#   "type": "string",
#   "sortby": "sortBySize",
#   "key": "u:d:d:i:2222:2463205",
#   "valsize": 1368783,
#   "fields": 1
# }
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为可读字符串"""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"


def _parse_bigkey_log(log_src: Dict) -> Optional[Dict]:
    """解析单条大key日志记录"""
    try:
        log_str = log_src.get("log", "")
        if log_str:
            try:
                log_data = json.loads(log_str)
            except (json.JSONDecodeError, TypeError):
                log_data = log_src
        else:
            log_data = log_src

        addr = log_data.get("addr", log_src.get("addr", ""))
        key = log_data.get("key", log_src.get("rediskey", ""))
        valsize = log_data.get("valsize", log_src.get("valsize", 0))
        key_type = log_data.get("type", log_src.get("type", ""))
        sortby = log_data.get("sortby", log_src.get("sortby", ""))
        top_idx = log_data.get("top_idx", log_src.get("top_idx", 0))
        fields = log_data.get("fields", log_src.get("fields", 0))
        timestamp = log_data.get("@timestamp", log_src.get("time", log_src.get("dtEventTimeStamp", "")))
        domain = log_data.get("domain", log_src.get("domain", ""))

        return {
            "addr": addr,
            "key": key,
            "valsize": valsize,
            "valsize_human": _format_size(valsize),
            "type": key_type,
            "sortby": sortby,
            "top_idx": top_idx,
            "fields": fields,
            "timestamp": timestamp,
            "domain": domain,
        }
    except Exception:
        return None


def _get_bigkey_logs(query_params: Dict) -> List[Dict]:
    """从BKLog查询大key日志"""
    try:
        resp = BKLogApi.esquery_search(query_params, use_admin=True)
        bigkey_logs = []
        for hit in resp.get("hits", {}).get("hits", []):
            log_src = hit.get("_source", None)
            if log_src is None:
                continue
            parsed = _parse_bigkey_log(log_src)
            if parsed:
                bigkey_logs.append(parsed)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query bigkey logs failed: {e}")
    return bigkey_logs


def _get_bigkey_query_params(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict:
    """构建大key日志查询参数"""
    query_parts = [f'domain:"{immute_domain}"']
    if host and port:
        query_parts.append(f'addr:"{host}:{port}"')
    elif host:
        query_parts.append(f'addr:"{host}:*"')

    return {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_bigkey",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": " AND ".join(query_parts),
        "start": 0,
        "size": 1000,
        "sort_list": [["dtEventTimeStamp", "desc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }


def get_cluster_bigkey_static(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    """获取集群时间范围内大key日志统计数据"""
    logs = _get_bigkey_logs(_get_bigkey_query_params(immute_domain, start_time, end_time))

    # 按实例维度聚合
    instance_data: Dict[str, Any] = defaultdict(lambda: {"keys": [], "total_size": 0, "type_count": defaultdict(int)})
    type_count: Dict[str, int] = defaultdict(int)
    total_size = 0

    for record in logs:
        addr = record.get("addr", "unknown")
        valsize = record.get("valsize", 0)
        key_type = record.get("type", "unknown")

        instance_data[addr]["keys"].append(record)
        instance_data[addr]["total_size"] += valsize
        instance_data[addr]["type_count"][key_type] += 1

        type_count[key_type] += 1
        total_size += valsize

    # 构建按实例统计结果
    by_instance = {}
    for addr, data in instance_data.items():
        keys = data["keys"]
        # 按valsize降序取top10
        top_keys = sorted(keys, key=lambda x: x.get("valsize", 0), reverse=True)[:10]
        by_instance[addr] = {
            "total_count": len(keys),
            "total_size": data["total_size"],
            "total_size_human": _format_size(data["total_size"]),
            "type_distribution": dict(data["type_count"]),
            "top_keys": top_keys,
        }

    return {
        "summary": {
            "total_count": len(logs),
            "instance_count": len(instance_data),
            "total_size": total_size,
            "total_size_human": _format_size(total_size),
            "type_distribution": dict(type_count),
        },
        "by_instance": by_instance,
    }


def get_host_or_instance_bigkey_logs(
    immute_domain: str,
    host: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    port: Optional[int] = None,
) -> Dict:
    """获取某台机器或某个实例上时间范围内大key日志（port 为空时查询整台机器）"""
    logs = _get_bigkey_logs(_get_bigkey_query_params(immute_domain, start_time, end_time, host=host, port=port))
    logs_sorted = sorted(logs, key=lambda x: x.get("valsize", 0), reverse=True)
    return {"total_count": len(logs_sorted), "bigkey_entries": logs_sorted}
