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
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

from backend import env
from backend.components import BKMonitorV3Api
from backend.dbm_aiagent.mcp_tools.redis.tools.comm_tools import parse_time2_long


def get_cluster_alarms(
    immute_domain: Optional[str] = None,
    start_time: Optional[Union[int, str, datetime]] = None,
    end_time: Optional[Union[int, str, datetime]] = None,
) -> List[Dict]:

    alarms = get_alarms_flat(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
    cluster_alarms = alarms.get(immute_domain, [])
    return {"total_alarms": len(cluster_alarms), "alarm_detail": cluster_alarms}


def get_alarms_flat(
    appid: Optional[Union[str, int]] = None,
    immute_domain: Optional[str] = None,
    start_time: Optional[Union[int, str, datetime]] = None,
    end_time: Optional[Union[int, str, datetime]] = None,
    n_hour: Optional[int] = None,
    limit: int = 5000,
) -> Dict[str, Dict[str, List[Dict]]]:
    """
    获取告警列表（更灵活的版本，支持同时指定多个条件和时间范围）

    Args:
        appid: 业务ID（可选）
        cluster_domain: 集群域名（可选）
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        n_hour: 查询最近N小时的告警（默认24小时）
        limit: 返回结果数量限制，默认5000
    """
    if not appid and not immute_domain:
        raise ValueError("必须指定appid或cluster_domain中的至少一个")

    # 处理时间参数
    if start_time is not None and end_time is not None:
        start_timestamp = parse_time2_long(start_time)
        end_timestamp = parse_time2_long(end_time)
    else:
        if n_hour is None:
            n_hour = 24
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - n_hour * 60 * 60

    # 构建查询条件
    query_conditions = ['labels: "DBM_REDIS"']

    if appid:
        query_conditions.append(f'tags.appid : "{appid}"')

    if immute_domain:
        query_conditions.append(f'tags.cluster_domain : "{immute_domain}"')

    query_string = " AND ".join(query_conditions)

    # 调用监控API
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

    # 解析告警数据
    alarms = {}

    for alt in data.get("alerts", []):
        alarm = {
            "alert_name": alt.get("alert_name", ""),
            "description": alt.get("description", ""),
            "begin_time": alt.get("begin_time", ""),
            "target_key": alt.get("target_key", ""),
        }

        # 提取tags信息
        for tag in alt.get("tags", []):
            alarm[tag["key"]] = tag["value"]

        # 获取集群域名和告警名称
        immute_domain = alarm.get("cluster_domain", "unknown")
        alert_name = alarm.get("alert_name", "unknown")

        # 移除不需要的字段
        alarm.pop("cluster_domain", None)
        alarm.pop("appid", None)

        # 按集群和告警名称分组
        if immute_domain not in alarms:
            alarms[immute_domain] = {}

        if alert_name not in alarms[immute_domain]:
            alarms[immute_domain][alert_name] = []

        alarms[immute_domain][alert_name].append(alarm)

    return alarms
