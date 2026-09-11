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
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple

from django.db.models import Count
from django.utils import timezone

from backend.db_meta.enums import InstanceStatus, MachineType
from backend.db_meta.models import Machine, StorageInstance
from backend.db_services.mongodb.autofix.enums import MONGO_AUTOFIX_ACTIVE_STATUSES
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("root")

# 会重启/替换 mongod 的单据类型（发现闸门）
RESTART_SHIELD_TICKET_TYPES = (
    TicketType.MONGODB_INSTANCE_RELOAD.value,
    TicketType.MONGODB_INSTANCE_FIX_STATUS.value,
    TicketType.MONGODB_AUTOFIX.value,
    TicketType.MONGODB_AUTOFIX_PRE.value,
    TicketType.MONGODB_CUTOFF.value,
    TicketType.MONGODB_REPLICASET_CUTOFF.value,
    TicketType.MONGODB_SHARD_CUTOFF.value,
    TicketType.MONGODB_SCALE_UPDOWN.value,
    TicketType.MONGODB_UPGRADE_VERSION.value,
    TicketType.MONGODB_REPLICASET_MIGRATE.value,
    TicketType.MONGODB_SHARD_MIGRATE.value,
    TicketType.MONGODB_ADD_SHARD_NODES.value,
    TicketType.MONGODB_SHARD_ADD_SHARD_NODES.value,
    TicketType.MONGODB_REPLICA_ADD_SHARD_NODES.value,
    TicketType.MONGODB_REDUCE_SHARD_NODES.value,
)

AF_TICKET_ACTIVE_STATUSES = list(TICKET_RUNNING_STATUS_SET) + [TicketStatus.PENDING.value]


@dataclass
class HostCandidate:
    """园区/城市熔断用的主机候选."""

    ip: str
    bk_host_id: int = 0
    bk_sub_zone_id: int = 0
    bk_city: str = ""
    cluster_ids: List[int] = field(default_factory=list)
    rs_keys: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)  # ip:port


@dataclass
class ZoneBreakerResult:
    passed: List[HostCandidate]
    suppressed: List[HostCandidate]
    reason_by_ip: Dict[str, str] = field(default_factory=dict)


def is_instance_running(storage: StorageInstance) -> bool:
    return storage.status == InstanceStatus.RUNNING.value


def zone_city_circuit_breaker(
    candidates: Iterable[HostCandidate],
    zone_total_hosts: Optional[Dict[int, int]] = None,
    zone_host_threshold: int = 3,
    zone_percent: float = 0.3,
    city_host_threshold: int = 5,
) -> ZoneBreakerResult:
    """
    纯函数：同园区 / 同城市批量异常熔断。

    - 同 bk_sub_zone_id：候选主机数 >= zone_host_threshold，或占 zone_total_hosts[zone] >= zone_percent
    - 同 bk_city：候选主机数 >= city_host_threshold
    命中则该园区/城市全部 suppress。
    """
    candidates = list(candidates)
    zone_total_hosts = zone_total_hosts or {}

    by_zone: Dict[int, List[HostCandidate]] = defaultdict(list)
    by_city: Dict[str, List[HostCandidate]] = defaultdict(list)
    for cand in candidates:
        by_zone[cand.bk_sub_zone_id].append(cand)
        if cand.bk_city:
            by_city[cand.bk_city].append(cand)

    suppressed_ips: Set[str] = set()
    reason_by_ip: Dict[str, str] = {}

    for zone_id, hosts in by_zone.items():
        if zone_id == 0:
            continue
        uniq = {h.ip: h for h in hosts}
        count = len(uniq)
        total = zone_total_hosts.get(zone_id) or 0
        hit_count = count >= zone_host_threshold
        hit_pct = total > 0 and (count / total) >= zone_percent
        if hit_count or hit_pct:
            reason = f"zone_breaker:zone={zone_id}:count={count}:total={total}"
            for ip in uniq:
                suppressed_ips.add(ip)
                reason_by_ip[ip] = reason

    for city, hosts in by_city.items():
        uniq = {h.ip: h for h in hosts}
        count = len(uniq)
        if count >= city_host_threshold:
            reason = f"city_breaker:city={city}:count={count}"
            for ip in uniq:
                suppressed_ips.add(ip)
                reason_by_ip[ip] = reason

    passed = [c for c in candidates if c.ip not in suppressed_ips]
    suppressed = [c for c in candidates if c.ip in suppressed_ips]
    return ZoneBreakerResult(passed=passed, suppressed=suppressed, reason_by_ip=reason_by_ip)


def same_rs_limit(
    candidates: Iterable[HostCandidate],
    active_names_by_rs: Optional[Dict[str, Set[str]]] = None,
    max_abnormal: int = 2,
) -> Tuple[List[HostCandidate], Dict[str, str]]:
    """
    纯函数：同 RS 已有 >= max_abnormal 个异常成员（含进行中 Core）则拒绝该 RS 全部候选。

    返回 (passed, reason_by_ip)。
    """
    active_names_by_rs = active_names_by_rs or {}
    candidates = list(candidates)

    abnormal_by_rs: Dict[str, Set[str]] = defaultdict(set)
    for rs_key, names in active_names_by_rs.items():
        abnormal_by_rs[rs_key].update(names)
    for cand in candidates:
        for rs_key in cand.rs_keys:
            abnormal_by_rs[rs_key].update(cand.names)

    blocked_rs = {rs_key for rs_key, names in abnormal_by_rs.items() if len(names) >= max_abnormal}

    reason_by_ip: Dict[str, str] = {}
    passed: List[HostCandidate] = []
    for cand in candidates:
        hit = cand.rs_keys & blocked_rs
        if hit:
            reason_by_ip[cand.ip] = f"same_rs_limit:rs={','.join(sorted(hit))}"
            continue
        passed.append(cand)
    return passed, reason_by_ip


def has_active_autofix_core(ip: str) -> bool:
    return MongoAutofixCore.objects.filter(ip=ip, deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES).exists()


def _extract_ticket_ips_and_hosts(ticket: Ticket) -> Tuple[Set[str], Set[int]]:
    details = ticket.details or {}
    ips: Set[str] = set()
    host_ids: Set[int] = set()

    for ip in get_target_items_from_details(details, match_keys=["ip"]):
        if isinstance(ip, str) and ip:
            ips.add(ip)

    for hid in get_target_items_from_details(details, match_keys=["bk_host_id", "bk_host_ids", "host_id"]):
        try:
            host_ids.add(int(hid))
        except (TypeError, ValueError):
            continue

    # AUTOFIX: mongod_list / mongos_list
    for info in details.get("infos") or []:
        if not isinstance(info, dict):
            continue
        for key in ("mongod_list", "mongos_list", "mongodb", "mongo_config"):
            for host in info.get(key) or []:
                if isinstance(host, dict):
                    if host.get("ip"):
                        ips.add(host["ip"])
                    if host.get("bk_host_id"):
                        try:
                            host_ids.add(int(host["bk_host_id"]))
                        except (TypeError, ValueError):
                            pass

    return ips, host_ids


def build_restart_shield_sets(
    lookback_days: int = 7,
) -> Tuple[Set[str], Set[int], Set[int]]:
    """
    扫描近期活跃 Mongo 变更/重启单据，返回 (shielded_ips, shielded_host_ids, cluster_fallback_ids)。
    cluster_fallback_ids：抽不到 IP 时降级用的集群 ID。
    """
    since = timezone.now() - timedelta(days=lookback_days)
    qs = Ticket.objects.filter(
        ticket_type__in=RESTART_SHIELD_TICKET_TYPES,
        status__in=AF_TICKET_ACTIVE_STATUSES,
        create_at__gte=since,
    ).only("id", "ticket_type", "details", "status")

    shielded_ips: Set[str] = set()
    shielded_hosts: Set[int] = set()
    cluster_fallback: Set[int] = set()

    for ticket in qs.iterator(chunk_size=200):
        ips, hosts = _extract_ticket_ips_and_hosts(ticket)
        if ips or hosts:
            shielded_ips.update(ips)
            shielded_hosts.update(hosts)
            continue
        # 抽不到 IP 时降级：整集群屏蔽（宁可漏修）
        try:
            cluster_fallback.update(fetch_cluster_ids(ticket.details or {}))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mongo autofix shield fetch_cluster_ids fail ticket=%s err=%s", ticket.id, exc)

    return shielded_ips, shielded_hosts, cluster_fallback


def is_restart_shielded(
    ip: str,
    bk_host_id: int,
    cluster_ids: Optional[List[int]] = None,
    shielded_ips: Optional[Set[str]] = None,
    shielded_hosts: Optional[Set[int]] = None,
    cluster_fallback: Optional[Set[int]] = None,
) -> bool:
    """
    重启/变更单据屏蔽 + 同 IP 活跃 Core。
    可传入预构建的 shield sets 以避免每候选重复扫库。
    """
    if has_active_autofix_core(ip):
        return True

    if shielded_ips is None or shielded_hosts is None or cluster_fallback is None:
        shielded_ips, shielded_hosts, cluster_fallback = build_restart_shield_sets()

    if ip in shielded_ips:
        return True
    if bk_host_id and bk_host_id in shielded_hosts:
        return True
    if cluster_ids and cluster_fallback:
        if set(cluster_ids) & cluster_fallback:
            return True
    return False


def count_mongo_hosts_by_zone(zone_ids: Iterable[int]) -> Dict[int, int]:
    """统计各园区 mongodb/mongo_config 主机数，供园区占比熔断."""
    zone_ids = [zid for zid in set(zone_ids) if zid]
    if not zone_ids:
        return {}
    rows = (
        Machine.objects.filter(
            bk_sub_zone_id__in=zone_ids,
            machine_type__in=[MachineType.MONGODB.value, MachineType.MONOG_CONFIG.value],
        )
        .values("bk_sub_zone_id")
        .annotate(host_count=Count("bk_host_id"))
    )
    return {row["bk_sub_zone_id"]: row["host_count"] for row in rows}
