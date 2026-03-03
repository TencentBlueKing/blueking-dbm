"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

from backend import env
from backend.components import BKMonitorV3Api
from backend.dbm_aiagent.mcp_tools.mongodb.tools.comm_tools import parse_time2_long


def get_cluster_alarms(
    immute_domain: Optional[str] = None,
    start_time: Optional[Union[int, str, datetime]] = None,
    end_time: Optional[Union[int, str, datetime]] = None,
) -> Dict:
    alarms = get_alarms_flat(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
    by_alert = cast(
        Dict[str, List[Any]],
        alarms.get(immute_domain, {}) if immute_domain is not None else {},
    )
    cluster_alarms = [{"alert_name": k, "alert_detail": v} for k, v in by_alert.items()]
    total = sum(len(v) for v in by_alert.values())
    return {"total_alarms": total, "alarm_detail": cluster_alarms}


def get_alarms_flat(
    appid: Optional[Union[str, int]] = None,
    immute_domain: Optional[str] = None,
    start_time: Optional[Union[int, str, datetime]] = None,
    end_time: Optional[Union[int, str, datetime]] = None,
    n_hour: Optional[int] = None,
    limit: int = 5000,
) -> Dict[str, List]:
    """获取告警列表，支持按业务或集群筛选。标签使用 DBM_MONGODB。"""
    if not appid and not immute_domain:
        raise ValueError("必须指定 appid 或 immute_domain 中的至少一个")
    if start_time is not None and end_time is not None:
        start_timestamp = parse_time2_long(start_time)
        end_timestamp = parse_time2_long(end_time)
    else:
        n_hour = n_hour or 24
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - n_hour * 60 * 60
    query_conditions = ['labels: "DBM_MONGODB"']
    if appid:
        query_conditions.append(f'tags.appid : "{appid}"')
    if immute_domain:
        query_conditions.append(f'tags.cluster_domain : "{immute_domain}"')
    query_string = " AND ".join(query_conditions)
    data = BKMonitorV3Api.search_alert(
        {
            "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "offset": 0,
            "limit": limit,
            "query_string": query_string,
        }
    )
    # 与 Redis 一致：alerts 列表，按 domain -> alert_name -> list 聚合
    result = {}
    for alt in data.get("alerts", []):
        alarm = {
            "alert_name": alt.get("alert_name", ""),
            "description": alt.get("description", ""),
            "begin_time": alt.get("begin_time", 0),
            "target_key": alt.get("target_key", ""),
        }
        for tag in alt.get("tags", []):
            alarm[tag["key"]] = tag["value"]
        immute_domain = alarm.get("cluster_domain", "unknown")
        alert_name = alarm.get("alert_name", "unknown")
        alarm.pop("cluster_domain", None)
        alarm.pop("appid", None)
        if immute_domain not in result:
            result[immute_domain] = {}
        if alert_name not in result[immute_domain]:
            result[immute_domain][alert_name] = []
        result[immute_domain][alert_name].append(alarm)
    return result
