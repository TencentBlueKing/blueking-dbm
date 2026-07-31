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
import re
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
        raise ValueError("At least one of appid or cluster_domain must be specified")

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


# Lucene query_string 语法保留字符，精确匹配时需要转义
_LUCENE_RESERVED_CHARS = r'\+-!(){}[]^"~:/'


def _escape_lucene(value: str) -> str:
    """对 Lucene query_string 语法中的保留字符进行反斜杠转义（用于精确匹配场景）"""
    escaped = []
    for ch in value:
        if ch in _LUCENE_RESERVED_CHARS:
            escaped.append("\\" + ch)
        else:
            escaped.append(ch)
    return "".join(escaped)


def _build_alert_name_matcher(pattern: str, match_mode: str):
    """
    根据 match_mode 返回一个 (alert_name: str) -> bool 的匹配器，用于在内存中过滤告警。

    - fuzzy: 包含匹配（substring）
    - wildcard: 将 * 转成 .*，? 转成 . 后做 re.fullmatch
    - exact: 完全相等
    """
    if match_mode == "fuzzy":
        return lambda name: pattern in (name or "")
    if match_mode == "wildcard":
        # 把 * ? 之外的字符全部转义，避免用户输入中的正则元字符造成误匹配
        regex_parts = []
        for ch in pattern:
            if ch == "*":
                regex_parts.append(".*")
            elif ch == "?":
                regex_parts.append(".")
            else:
                regex_parts.append(re.escape(ch))
        regex = re.compile("".join(regex_parts))
        return lambda name: bool(regex.fullmatch(name or ""))
    # exact
    return lambda name: (name or "") == pattern


def get_alarms_by_alert_name(
    alert_name: str,
    start_time: Optional[Union[int, str, datetime]] = None,
    end_time: Optional[Union[int, str, datetime]] = None,
    n_minute: Optional[int] = None,
    fuzzy: bool = True,
    limit: int = 5000,
) -> Dict:
    """
    根据告警名称，获取指定时间范围内所有业务的该类告警详细。

    匹配策略：
    - fuzzy=True（默认）：客户端"包含匹配"。服务端只按 labels="DBM_REDIS" 拉数据，
      在内存中过滤 alert_name 是否包含用户输入的关键词，
      能可靠支持中文/含括号等特殊字符的告警名。
    - alert_name 含 * / ? ：按通配符模式做客户端 fullmatch，* 匹配任意字符，? 匹配单字符。
    - fuzzy=False：精确匹配（走服务端 query_string 短语精确匹配，最省流量）。

    Args:
        alert_name: 告警名称（必填）。支持三种输入形式：
            - 关键词： "主机内存使用率"，fuzzy=True 时匹配所有包含该关键词的告警
              （例如 "Redis(TendisPlus)主机内存使用率"、"xxx主机内存使用率-子告警" 等）
            - 通配符： "*主机内存使用率*"、"Redis*内存*"，按通配符做整串匹配
            - 精确匹配： fuzzy=False 时按完整告警名精确匹配
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        n_minute: 查询最近N分钟的告警（默认20分钟），当未同时指定 start_time/end_time 时生效
        fuzzy: 是否模糊匹配（默认 True）。仅当 alert_name 中不含 * / ? 时生效
        limit: 服务端拉取告警条数上限，默认5000

    Returns:
        {
            "query_name": "xxx",  # 用户传入的查询关键词/模式
            "match_mode": "fuzzy" | "wildcard" | "exact",
            "total_alarms": N,
            "alarm_list": [ {告警明细}, ... ]
        }
    """
    if not alert_name:
        raise ValueError("alert_name must be specified")

    # 处理时间参数
    if start_time is not None and end_time is not None:
        start_timestamp = parse_time2_long(start_time)
        end_timestamp = parse_time2_long(end_time)
    else:
        if n_minute is None:
            n_minute = 20
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - n_minute * 60

    # 判定匹配模式
    user_has_wildcard = ("*" in alert_name) or ("?" in alert_name)
    if user_has_wildcard:
        match_mode = "wildcard"
    elif fuzzy:
        match_mode = "fuzzy"
    else:
        match_mode = "exact"

    # 构建服务端 query_string：
    # - exact 模式下把 alert_name 交给服务端做短语精确匹配，减少数据量
    # - fuzzy / wildcard 模式下由于 ES query_string 对中文/含特殊字符的 wildcard 支持不稳定
    #   （分词器差异、性能限制等），改为只按 DBM_REDIS 拉全量数据后在客户端做过滤
    query_conditions = ['labels: "DBM_REDIS"']
    if match_mode == "exact":
        # 双引号内的双引号和反斜杠需要转义
        safe = alert_name.replace("\\", "\\\\").replace('"', '\\"')
        query_conditions.append(f'alert_name: "{safe}"')

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

    # 构造客户端过滤器（exact 模式无需再次过滤，但保留一致处理便于兜底）
    matcher = _build_alert_name_matcher(alert_name, match_mode)

    # 解析告警数据：直接扁平输出
    alarm_list: List[Dict] = []

    for alt in data.get("alerts", []):
        raw_alert_name = alt.get("alert_name", "")
        if not matcher(raw_alert_name):
            continue

        alarm = {
            "alert_name": raw_alert_name,
            "description": alt.get("description", ""),
            "begin_time": alt.get("begin_time", ""),
            "target_key": alt.get("target_key", ""),
        }

        # 提取tags信息（保留 appid、cluster_domain 等字段在明细中）
        for tag in alt.get("tags", []):
            alarm[tag["key"]] = tag["value"]

        alarm_list.append(alarm)

    return {
        "query_name": alert_name,
        "match_mode": match_mode,
        "total_alarms": len(alarm_list),
        "alarm_list": alarm_list,
    }
