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
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Iterable, List, Optional, Set

from django.utils import timezone

from backend.db_services.mongodb.autofix.enums import PEER_ABNORMAL_STATES

# Keep unify_query params local to avoid importing local_tasks package (registers celery at import).
_UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 0,
    "end_time": 0,
    "slimit": 500,
    "down_sample_range": "1s",
    "type": "instant",
}

logger = logging.getLogger("root")

# 新旧 exporter 指标名（OR 并集）
MEMBER_STATE_METRICS = (
    "bkmonitor:exporter_dbm_mongodb_exporter:mongodb_rs_members_state",
    "bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_member_state",
)

DISK_RW_OK_METRIC = "bkmonitor:exporter_dbm_mongodb_exporter:mongo_datadir_disk_rw_ok"

# 新指标用 name/set；旧 mongodb_rs_members_state 用 member_idx/rs_nm（无 self 时靠 reporter==name 剔自报）
PEER_QUERY_BY = (
    "name,member_idx,instance,bk_target_ip,instance_port," "shard,set,rs_nm,cluster_domain,self,instance_role"
)


@dataclass(frozen=True)
class PeerObservation:
    """旁观者视角的一条 member_state 观测."""

    name: str  # 目标成员 ip:port
    reporter: str  # 上报者 addr
    state: int
    cluster_domain: str = ""
    shard: str = ""
    set_name: str = ""
    metric_name: str = ""


@dataclass
class PeerAbnormalSummary:
    """按目标 name 聚合后的异常旁观者摘要（纯数据结构，便于单测）."""

    name: str
    reporters: Set[str] = field(default_factory=set)
    states: Set[int] = field(default_factory=set)
    cluster_domain: str = ""
    shard: str = ""
    set_name: str = ""

    @property
    def peer_count(self) -> int:
        return len(self.reporters)

    @property
    def rs_key(self) -> str:
        """同副本集键：域名 + shard/set."""
        group = self.shard or self.set_name or ""
        return f"{self.cluster_domain}|{group}"


def _extract_datapoint_value(item: dict):
    datapoints = item.get("datapoints") or []
    if not datapoints or not isinstance(datapoints[0], (list, tuple)) or len(datapoints[0]) == 0:
        return None
    return datapoints[0][0]


def _is_valid_addr(addr: str) -> bool:
    if not addr or ":" not in addr:
        return False
    host, port = addr.rsplit(":", 1)
    if not host or not port:
        return False
    try:
        int(port)
    except (TypeError, ValueError):
        return False
    return True


def _reporter_addr(dims: dict) -> str:
    instance = (dims.get("instance") or "").strip()
    if _is_valid_addr(instance):
        return instance
    # instance 维度有时是 ip-port
    if instance and "-" in instance and ":" not in instance:
        maybe = instance.replace("-", ":", 1)
        if _is_valid_addr(maybe):
            return maybe
    ip = (dims.get("bk_target_ip") or "").strip()
    port = dims.get("instance_port")
    if ip and port is not None and str(port) != "":
        return f"{ip}:{port}"
    return ip


def is_self_report(name: str, reporter: str, dims: dict) -> bool:
    """排除本机自报：self==1 或 reporter==name."""
    self_flag = str(dims.get("self", "")).strip()
    if self_flag == "1":
        return True
    if reporter and name and reporter == name:
        return True
    return False


def _target_member_name(dims: dict) -> str:
    """目标成员 ip:port：新指标 name，旧指标 member_idx。"""
    for key in ("name", "member_idx"):
        raw = (dims.get(key) or "").strip()
        if _is_valid_addr(raw):
            return raw
    return ""


def _set_name(dims: dict) -> str:
    """副本集名：新指标 set，旧指标 rs_nm。"""
    return (dims.get("set") or dims.get("rs_nm") or "").strip()


def parse_peer_series(series: list, metric_name: str = "") -> List[PeerObservation]:
    """纯函数：把 unify_query series 解析为 PeerObservation 列表."""
    observations: List[PeerObservation] = []
    for item in series or []:
        value = _extract_datapoint_value(item)
        if value is None:
            continue
        try:
            state = int(value)
        except (TypeError, ValueError):
            continue
        dims = item.get("dimensions") or {}
        name = _target_member_name(dims)
        if not name:
            continue
        reporter = _reporter_addr(dims)
        if not reporter:
            continue
        if is_self_report(name, reporter, dims):
            continue
        # 保留 instance_role 维度供排查；backup 仍是合法旁观者（m1+m2+backup 时 peer_min=2 需要它）
        observations.append(
            PeerObservation(
                name=name,
                reporter=reporter,
                state=state,
                cluster_domain=(dims.get("cluster_domain") or "").strip(),
                shard=(dims.get("shard") or "").strip(),
                set_name=_set_name(dims),
                metric_name=metric_name,
            )
        )
    return observations


def aggregate_abnormal_peers(
    observations: Iterable[PeerObservation],
    abnormal_states: Set[int] | frozenset = PEER_ABNORMAL_STATES,
) -> Dict[str, PeerAbnormalSummary]:
    """
    纯函数：按目标 name 聚合异常旁观者。
    仅统计 state ∈ abnormal_states 的互异 reporter。
    """
    result: Dict[str, PeerAbnormalSummary] = {}
    for obs in observations:
        if obs.state not in abnormal_states:
            continue
        summary = result.get(obs.name)
        if summary is None:
            summary = PeerAbnormalSummary(
                name=obs.name,
                cluster_domain=obs.cluster_domain,
                shard=obs.shard,
                set_name=obs.set_name,
            )
            result[obs.name] = summary
        summary.reporters.add(obs.reporter)
        summary.states.add(obs.state)
        # 补全空维度
        if not summary.cluster_domain and obs.cluster_domain:
            summary.cluster_domain = obs.cluster_domain
        if not summary.shard and obs.shard:
            summary.shard = obs.shard
        if not summary.set_name and obs.set_name:
            summary.set_name = obs.set_name
    return result


def filter_by_peer_min(
    aggregated: Dict[str, PeerAbnormalSummary], peer_min_count: int
) -> Dict[str, PeerAbnormalSummary]:
    """纯函数：旁观者人数门槛."""
    return {name: s for name, s in aggregated.items() if s.peer_count >= peer_min_count}


def is_delay_satisfied(first_seen_ts: Optional[int], now_ts: int, delay_minutes: int) -> bool:
    """纯函数：是否已持续达到延迟窗口."""
    if first_seen_ts is None:
        return False
    if delay_minutes <= 0:
        return True
    return now_ts - int(first_seen_ts) >= delay_minutes * 60


def peer_first_seen_key(name: str) -> str:
    return f"mongo|autofix|peer|{name}"


def _unify_query(promql: str, minutes: int = 5, retry_times: int = 2) -> Optional[list]:
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)
    from backend import env
    from backend.components import BKMonitorV3Api

    params = copy.deepcopy(_UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    params["slimit"] = 5000
    params["query_configs"][0]["promql"] = promql
    last_err = None
    for i in range(retry_times):
        try:
            out = BKMonitorV3Api.unify_query(params, use_admin=True)
            return out.get("series") or []
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("mongo autofix unify_query retry=%s/%s err=%s", i + 1, retry_times, exc)
            if i < retry_times - 1:
                time.sleep(2)
    logger.error("mongo autofix unify_query failed: %s promql=%s", last_err, promql)
    return None


def _member_state_promql(metric_name: str) -> str:
    return f"avg by ({PEER_QUERY_BY}) ({metric_name})"


def query_peer_member_states(minutes: int = 5) -> Optional[List[PeerObservation]]:
    """
    查询旁观者 member_state（新旧指标名并集）。
    API 全部失败 → None（平台不可用）；任一成功 → list（可为空）。
    """
    observations: List[PeerObservation] = []
    any_ok = False
    for metric_name in MEMBER_STATE_METRICS:
        series = _unify_query(_member_state_promql(metric_name), minutes=minutes)
        if series is None:
            continue
        any_ok = True
        observations.extend(parse_peer_series(series, metric_name=metric_name))
    if not any_ok:
        return None

    # 同 (name, reporter) 去重，保留最后一条
    dedup: Dict[tuple, PeerObservation] = {}
    for obs in observations:
        dedup[(obs.name, obs.reporter)] = obs
    return list(dedup.values())


def query_disk_rw_ok(cluster_domain: str | None = None, minutes: int = 5) -> Optional[Dict[str, int]]:
    """
    可选：查询 mongo_datadir_disk_rw_ok。
    返回 {ip:port -> 0/1}；API 失败 → None；缺指标当空 dict。
    """
    if cluster_domain:
        cond = f'{{cluster_domain="{cluster_domain}"}}'
    else:
        cond = ""
    promql = "avg by (cluster_domain,instance,bk_target_ip,instance_port) (" f"{DISK_RW_OK_METRIC}{cond}" ")"
    series = _unify_query(promql, minutes=minutes)
    if series is None:
        return None
    result: Dict[str, int] = {}
    for item in series:
        value = _extract_datapoint_value(item)
        if value is None:
            continue
        dims = item.get("dimensions") or {}
        instance = (dims.get("instance") or "").strip()
        if not _is_valid_addr(instance):
            ip = (dims.get("bk_target_ip") or "").strip()
            port = dims.get("instance_port")
            if not ip or port is None:
                continue
            instance = f"{ip}:{port}"
        try:
            result[instance] = int(value)
        except (TypeError, ValueError):
            continue
    return result


def group_abnormal_names_by_rs(summaries: Dict[str, PeerAbnormalSummary]) -> Dict[str, Set[str]]:
    """纯函数：rs_key → 异常目标 name 集合."""
    grouped: Dict[str, Set[str]] = defaultdict(set)
    for name, summary in summaries.items():
        grouped[summary.rs_key].add(name)
    return grouped
