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
# 热key日志示例：
# {
#   "app": "11",
#   "addr": "1.4.202.34:30016",
#   "domain": "s.mobile.333.db",
#   "@timestamp": "2026-04-10T11:21:37+08:00",
#   "key_cnt": 100,
#   "key_ops": "12345",
#   "key_ratio": 0.35,
#   "key_sample": "u:d:d:i:2222:2463205"
# }
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.time import datetime2str


def _to_int(val: Any, default: int = 0) -> int:
    """尝试将值转换为 int，转换失败时返回默认值"""
    try:
        if val is None or val == "":
            return default
        return int(val)
    except (TypeError, ValueError):
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return default


def _to_float(val: Any, default: float = 0.0) -> float:
    """尝试将值转换为 float，转换失败时返回默认值"""
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_hotkey_log(log_src: Dict) -> Optional[Dict]:
    """解析单条热key日志记录"""
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
        key_cnt = _to_int(log_data.get("key_cnt", log_src.get("key_cnt", 0)))
        key_ops = _to_int(log_data.get("key_ops", log_src.get("key_ops", 0)))
        key_ratio = _to_float(log_data.get("key_ratio", log_src.get("key_ratio", 0)))
        key_sample = log_data.get("key_sample", log_src.get("key_sample", ""))
        timestamp = log_data.get("@timestamp", log_src.get("time", log_src.get("dtEventTimeStamp", "")))
        domain = log_data.get("domain", log_src.get("domain", ""))

        return {
            "addr": addr,
            "key_sample": key_sample,
            "key_cnt": key_cnt,
            "key_ops": key_ops,
            "key_ratio": round(key_ratio, 4),
            "timestamp": timestamp,
            "domain": domain,
        }
    except Exception:
        return None


def _get_hotkey_logs(query_params: Dict) -> List[Dict]:
    """从BKLog查询热key日志"""
    try:
        resp = BKLogApi.esquery_search(query_params, use_admin=True)
        hotkey_logs = []
        for hit in resp.get("hits", {}).get("hits", []):
            log_src = hit.get("_source", None)
            if log_src is None:
                continue
            parsed = _parse_hotkey_log(log_src)
            if parsed:
                hotkey_logs.append(parsed)
    except Exception as e:
        raise DBMMcpBaseException(msg=f"query hotkey logs failed: {e}")
    return hotkey_logs


def _get_hotkey_query_params(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> Dict:
    """构建热key日志查询参数"""
    query_parts = [f'domain:"{immute_domain}"']
    if host and port:
        query_parts.append(f'addr:"{host}:{port}"')
    elif host:
        query_parts.append(f'addr:"{host}:*"')

    return {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_hotkey",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": " AND ".join(query_parts),
        "start": 0,
        "size": 1000,
        "sort_list": [["dtEventTimeStamp", "desc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }


def get_cluster_hotkey_static(
    immute_domain: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
) -> Dict:
    """获取集群时间范围内热key日志统计数据"""
    logs = _get_hotkey_logs(_get_hotkey_query_params(immute_domain, start_time, end_time))

    # 按实例维度聚合
    instance_data: Dict[str, Any] = defaultdict(lambda: {"keys": [], "total_ops": 0})
    total_ops = 0

    for record in logs:
        addr = record.get("addr", "unknown")
        key_ops = record.get("key_ops", 0)

        instance_data[addr]["keys"].append(record)
        instance_data[addr]["total_ops"] += key_ops

        total_ops += key_ops

    # 构建按实例统计结果（按key_ops降序取Top10）
    by_instance = {}
    for addr, data in instance_data.items():
        keys = data["keys"]
        top_keys = sorted(keys, key=lambda x: x.get("key_ops", 0), reverse=True)[:10]
        by_instance[addr] = {
            "total_count": len(keys),
            "total_ops": data["total_ops"],
            "top_keys": top_keys,
        }

    return {
        "summary": {
            "total_count": len(logs),
            "instance_count": len(instance_data),
            "total_ops": total_ops,
        },
        "by_instance": by_instance,
    }


def get_host_or_instance_hotkey_logs(
    immute_domain: str,
    host: str,
    start_time: timezone.datetime,
    end_time: timezone.datetime,
    port: Optional[int] = None,
) -> Dict:
    """获取某台机器或某个实例上时间范围内热key日志（port 为空时查询整台机器），按 key_ops 降序"""
    logs = _get_hotkey_logs(_get_hotkey_query_params(immute_domain, start_time, end_time, host=host, port=port))
    logs_sorted = sorted(logs, key=lambda x: x.get("key_ops", 0), reverse=True)
    return {"total_count": len(logs_sorted), "hotkey_entries": logs_sorted}
