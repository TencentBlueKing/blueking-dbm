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
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

from django.utils import timezone
from django.utils.crypto import get_random_string

from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import StorageInstance
from backend.db_services.mongodb.autofix import ctl
from backend.db_services.mongodb.autofix.enums import (
    MONGO_AUTOFIX_ACTIVE_STATUSES,
    MongoAutofixLogEvent,
    MongoAutofixStatus,
)
from backend.db_services.mongodb.autofix.gates import (
    HostCandidate,
    build_restart_shield_sets,
    count_mongo_hosts_by_zone,
    is_restart_shielded,
    same_rs_limit,
    zone_city_circuit_breaker,
)
from backend.db_services.mongodb.autofix.log import write_autofix_log
from backend.db_services.mongodb.autofix.metrics import (
    PeerAbnormalSummary,
    aggregate_abnormal_peers,
    filter_by_peer_min,
    is_delay_satisfied,
    peer_first_seen_key,
    query_disk_rw_ok,
    query_peer_member_states,
)
from backend.db_services.mongodb.autofix.models import MongoAutofixCore, MongoIgnoreAutofix
from backend.db_services.mongodb.autofix.ticket_create import create_autofix_pre_ticket
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

MONGO_STORAGE_CLUSTER_TYPES = (
    ClusterType.MongoReplicaSet.value,
    ClusterType.MongoShardedCluster.value,
)


def touch_peer_first_seen(name: str, ttl_seconds: int, now_ts: Optional[int] = None) -> int:
    """
    Redis SET NX 记录首次异常时间；已存在则返回原时间戳并续期。
    纯逻辑配合 Redis：便于单测替换 RedisConn。
    """
    now_ts = int(now_ts if now_ts is not None else time.time())
    key = peer_first_seen_key(name)
    created = RedisConn.set(key, str(now_ts), nx=True, ex=ttl_seconds)
    if created:
        return now_ts
    raw = RedisConn.get(key)
    if raw is None:
        RedisConn.set(key, str(now_ts), ex=ttl_seconds)
        return now_ts
    try:
        first_seen = int(raw)
    except (TypeError, ValueError):
        first_seen = now_ts
        RedisConn.set(key, str(now_ts), ex=ttl_seconds)
        return first_seen
    RedisConn.expire(key, ttl_seconds)
    return first_seen


def clear_peer_first_seen(name: str) -> None:
    RedisConn.delete(peer_first_seen_key(name))


def disk_rw_first_seen_key(name: str) -> str:
    return f"mongo|autofix|disk_rw|{name}"


def touch_disk_rw_first_seen(name: str, ttl_seconds: int, now_ts: Optional[int] = None) -> int:
    now_ts = int(now_ts if now_ts is not None else time.time())
    key = disk_rw_first_seen_key(name)
    created = RedisConn.set(key, str(now_ts), nx=True, ex=ttl_seconds)
    if created:
        return now_ts
    raw = RedisConn.get(key)
    if raw is None:
        RedisConn.set(key, str(now_ts), ex=ttl_seconds)
        return now_ts
    try:
        first_seen = int(raw)
    except (TypeError, ValueError):
        first_seen = now_ts
        RedisConn.set(key, str(now_ts), ex=ttl_seconds)
        return first_seen
    RedisConn.expire(key, ttl_seconds)
    return first_seen


def clear_disk_rw_first_seen(name: str) -> None:
    RedisConn.delete(disk_rw_first_seen_key(name))


def _merge_disk_rw_candidates(
    sustained: Dict[str, PeerAbnormalSummary],
    delay_minutes: int,
    ttl_seconds: int,
    now_ts: int,
) -> Dict[str, int]:
    """
    场景2：旁观者仍可能报健康，但 dbmon 报 disk_rw_ok=0。
    返回 name -> 0（仅持续过延迟窗口的只读盘）。
    """
    disk_map = query_disk_rw_ok()
    if disk_map is None:
        logger.warning("mongo autofix disk_rw query failed, skip disk-only discovery")
        return {}
    if disk_map == {}:
        return {}

    disk_failed: Dict[str, int] = {}
    for name, val in disk_map.items():
        if val != 0:
            clear_disk_rw_first_seen(name)
            continue
        if name in sustained:
            disk_failed[name] = 0
            continue
        first_seen = touch_disk_rw_first_seen(name, ttl_seconds=ttl_seconds, now_ts=now_ts)
        if is_delay_satisfied(first_seen, now_ts, delay_minutes):
            disk_failed[name] = 0
            # 合成一个最小 PeerAbnormalSummary，便于复用 _aggregate_by_ip
            if name not in sustained:
                sustained[name] = PeerAbnormalSummary(name=name)
        else:
            logger.info("mongo autofix disk_rw delay wait name=%s", name)
    return disk_failed


def _record_ignore(
    *,
    bk_cloud_id: int,
    bk_biz_id: int,
    cluster_id: int,
    cluster_type: str,
    immute_domain: str,
    bk_host_id: int,
    ip: str,
    ignore_msg: str,
    extra: Optional[dict] = None,
) -> None:
    try:
        MongoIgnoreAutofix.objects.create(
            bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            cluster_id=cluster_id or 0,
            cluster_type=cluster_type or "",
            immute_domain=immute_domain or "",
            bk_host_id=bk_host_id or 0,
            ip=ip,
            ignore_msg=ignore_msg[:64],
            extra=extra or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("mongo autofix ignore write fail ip=%s err=%s", ip, exc)


def _parse_name(name: str) -> Optional[tuple]:
    if not name or ":" not in name:
        return None
    ip, port_str = name.rsplit(":", 1)
    try:
        return ip, int(port_str)
    except (TypeError, ValueError):
        return None


def _city_name(machine) -> str:
    try:
        if machine.bk_city_id and machine.bk_city:
            if getattr(machine.bk_city, "logical_city", None):
                return machine.bk_city.logical_city.name or machine.bk_city.bk_idc_city_name or ""
            return machine.bk_city.bk_idc_city_name or ""
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _load_running_storages(names: List[str], enable_configsvr: bool) -> Dict[str, StorageInstance]:
    """name(ip:port) → StorageInstance（status=running，mongodb；config 受开关控制）."""
    ip_ports = []
    for name in names:
        parsed = _parse_name(name)
        if parsed:
            ip_ports.append(parsed)
    if not ip_ports:
        return {}

    machine_types = [MachineType.MONGODB.value]
    if enable_configsvr:
        machine_types.append(MachineType.MONOG_CONFIG.value)

    # OR 过长时分批
    result: Dict[str, StorageInstance] = {}
    batch = 100
    for i in range(0, len(ip_ports), batch):
        chunk = ip_ports[i : i + batch]
        from django.db.models import Q

        query = Q()
        for ip, port in chunk:
            query |= Q(machine__ip=ip, port=port)
        qs = (
            StorageInstance.objects.filter(query)
            .filter(
                status=InstanceStatus.RUNNING.value,
                machine_type__in=machine_types,
                cluster_type__in=MONGO_STORAGE_CLUSTER_TYPES,
            )
            .exclude(instance_role=InstanceRole.MONGO_BACKUP.value)
            .select_related("machine", "machine__bk_city", "machine__bk_city__logical_city")
            .prefetch_related("cluster")
        )
        for storage in qs:
            key = f"{storage.machine.ip}:{storage.port}"
            result[key] = storage
    return result


def _aggregate_by_ip(
    sustained: Dict[str, PeerAbnormalSummary],
    storages: Dict[str, StorageInstance],
) -> Dict[str, HostCandidate]:
    by_ip: Dict[str, HostCandidate] = {}
    for name, summary in sustained.items():
        storage = storages.get(name)
        if storage is None:
            continue
        machine = storage.machine
        cluster = storage.cluster.first()
        if cluster is None:
            continue
        if not ctl.is_whitelist_allowed(cluster.bk_biz_id, cluster.immute_domain):
            continue
        cand = by_ip.get(machine.ip)
        if cand is None:
            cand = HostCandidate(
                ip=machine.ip,
                bk_host_id=machine.bk_host_id,
                bk_sub_zone_id=machine.bk_sub_zone_id or 0,
                bk_city=_city_name(machine),
            )
            by_ip[machine.ip] = cand
        cand.names.add(name)
        cand.rs_keys.add(summary.rs_key)
        if cluster.id not in cand.cluster_ids:
            cand.cluster_ids.append(cluster.id)
        # 附加元数据供建 Core（挂在对象动态属性上，避免改 dataclass）
        meta = getattr(cand, "_meta_storages", None)
        if meta is None:
            meta = []
            setattr(cand, "_meta_storages", meta)
        meta.append(storage)
        setattr(cand, "_summary", summary)
    return by_ip


def _active_core_names_by_rs() -> Dict[str, Set[str]]:
    """进行中 Core：按 immute_domain|（缺 shard 时的粗键）登记异常 name，防同 RS 并发."""
    result: Dict[str, Set[str]] = defaultdict(set)
    for core in MongoAutofixCore.objects.filter(deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES).iterator():
        ports = core.ports or []
        names = {f"{core.ip}:{port}" for port in ports} if ports else {f"{core.ip}:0"}
        # 粗键：仅域名，与 metrics 的 domain|shard 在 same_rs_limit 中通过候选自身 rs_key 聚合；
        # 另用 domain|* 前缀匹配不现实，这里把 active names 挂到每个候选可能撞上的 domain| 前缀。
        # 实际并发防护主要靠同 IP active Core；跨 IP 同 RS 依赖本轮 sustained 聚合。
        result[f"{core.immute_domain}|"].update(names)
    return result


def _create_core_for_candidate(cand: HostCandidate) -> Optional[MongoAutofixCore]:
    storages: List[StorageInstance] = getattr(cand, "_meta_storages", []) or []
    if not storages:
        return None
    primary = storages[0]
    cluster = primary.cluster.first()
    if cluster is None:
        return None

    ports = sorted({s.port for s in storages})
    roles = [s.instance_role for s in storages]
    cluster_ids = sorted({c.id for s in storages for c in s.cluster.all()})
    if not cluster_ids:
        cluster_ids = [cluster.id]

    fault_machines = [
        {
            "ip": cand.ip,
            "bk_host_id": cand.bk_host_id,
            "ports": ports,
            "roles": roles,
            "machine_type": primary.machine_type,
        }
    ]

    if MongoAutofixCore.objects.filter(ip=cand.ip, deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES).exists():
        logger.info("mongo autofix skip create, active core exists ip=%s", cand.ip)
        return None

    disk_rw_ok = getattr(cand, "_disk_rw_ok", -1)
    core = MongoAutofixCore.objects.create(
        bk_cloud_id=primary.machine.bk_cloud_id,
        bk_biz_id=cluster.bk_biz_id,
        cluster_id=cluster.id,
        cluster_type=cluster.cluster_type,
        immute_domain=cluster.immute_domain,
        fault_machines=fault_machines,
        ip=cand.ip,
        bk_host_id=cand.bk_host_id,
        cluster_ids=cluster_ids,
        ports=ports,
        roles=roles,
        bk_city=cand.bk_city,
        bk_sub_zone_id=cand.bk_sub_zone_id,
        deal_status=MongoAutofixStatus.DETECTED.value,
        status_version=get_random_string(12),
        disk_rw_ok=disk_rw_ok,
        detected_at=timezone.now(),
    )
    write_autofix_log(
        MongoAutofixLogEvent.DETECTED,
        f"detected fault ip={cand.ip} ports={ports} disk_rw_ok={disk_rw_ok}",
        core=core,
        context={"ports": ports, "roles": roles, "disk_rw_ok": disk_rw_ok},
    )
    return core


def _collect_sustained_peers(
    observations, peer_min: int, delay_minutes: int, ttl_seconds: int, now_ts: int
) -> Dict[str, PeerAbnormalSummary]:
    """聚合旁观者异常并套延迟窗口，返回 sustained name → summary。"""
    aggregated = aggregate_abnormal_peers(observations)
    abnormal_names = set(aggregated.keys())
    # 仅对达到 peer_min 的目标累计延迟；未达门槛也清掉窗口，避免单旁观者长期占 key
    qualified = filter_by_peer_min(aggregated, peer_min)

    # 扫描可能残留的 key 代价高；只清「曾在 qualified 路径」的，由 TTL 兜底。
    # 对当前仍异常但未达 peer_min 的，主动 clear。
    for name in abnormal_names - set(qualified.keys()):
        clear_peer_first_seen(name)

    sustained: Dict[str, PeerAbnormalSummary] = {}
    for name, summary in qualified.items():
        first_seen = touch_peer_first_seen(name, ttl_seconds=ttl_seconds, now_ts=now_ts)
        if is_delay_satisfied(first_seen, now_ts, delay_minutes):
            sustained[name] = summary
        else:
            logger.info(
                "mongo autofix delay wait name=%s peers=%s first_seen=%s delay=%sm",
                name,
                summary.peer_count,
                first_seen,
                delay_minutes,
            )
    return sustained


def _apply_zone_city_gates(candidates: List[HostCandidate]) -> List[HostCandidate]:
    """园区/城市熔断，返回通过候选。"""
    zone_totals = count_mongo_hosts_by_zone(c.bk_sub_zone_id for c in candidates)
    breaker = zone_city_circuit_breaker(
        candidates,
        zone_total_hosts=zone_totals,
        zone_host_threshold=ctl.get_zone_host_threshold(),
        zone_percent=ctl.get_zone_percent_threshold(),
        city_host_threshold=ctl.get_city_host_threshold(),
    )
    for cand in breaker.suppressed:
        _record_ignore(
            bk_cloud_id=0,
            bk_biz_id=0,
            cluster_id=(cand.cluster_ids[0] if cand.cluster_ids else 0),
            cluster_type="",
            immute_domain="",
            bk_host_id=cand.bk_host_id,
            ip=cand.ip,
            ignore_msg="zone_or_city_outage",
            extra={"reason": breaker.reason_by_ip.get(cand.ip, "")},
        )
    return breaker.passed


def _apply_same_rs_gates(
    candidates: List[HostCandidate],
    sustained: Dict[str, PeerAbnormalSummary],
    by_ip: Dict[str, HostCandidate],
) -> List[HostCandidate]:
    """同 RS 限制，返回通过候选。"""
    active_by_rs = _active_core_names_by_rs()
    # 合并本轮 sustained 精确 rs_key；并把同域名粗键上的 active Core 并入
    for name, summary in sustained.items():
        active_by_rs[summary.rs_key].add(name)
        coarse = f"{summary.cluster_domain}|"
        if summary.cluster_domain and coarse in active_by_rs:
            active_by_rs[summary.rs_key].update(active_by_rs[coarse])
    candidates, rs_reasons = same_rs_limit(candidates, active_names_by_rs=active_by_rs, max_abnormal=2)
    for ip, reason in rs_reasons.items():
        cand = by_ip.get(ip)
        _record_ignore(
            bk_cloud_id=0,
            bk_biz_id=0,
            cluster_id=(cand.cluster_ids[0] if cand and cand.cluster_ids else 0),
            cluster_type="",
            immute_domain="",
            bk_host_id=(cand.bk_host_id if cand else 0),
            ip=ip,
            ignore_msg="same_rs_limit",
            extra={"reason": reason},
        )
    return candidates


def _filter_restart_shielded(candidates: List[HostCandidate]) -> List[HostCandidate]:
    """重启单据屏蔽。"""
    shielded_ips, shielded_hosts, cluster_fallback = build_restart_shield_sets()
    surviving: List[HostCandidate] = []
    for cand in candidates:
        if is_restart_shielded(
            cand.ip,
            cand.bk_host_id,
            cluster_ids=cand.cluster_ids,
            shielded_ips=shielded_ips,
            shielded_hosts=shielded_hosts,
            cluster_fallback=cluster_fallback,
        ):
            _record_ignore(
                bk_cloud_id=0,
                bk_biz_id=0,
                cluster_id=(cand.cluster_ids[0] if cand.cluster_ids else 0),
                cluster_type="",
                immute_domain="",
                bk_host_id=cand.bk_host_id,
                ip=cand.ip,
                ignore_msg="restart_ticket_or_cooldown",
            )
            continue
        surviving.append(cand)
    return surviving


def _create_cores_and_pre(surviving: List[HostCandidate]) -> List[MongoAutofixCore]:
    """写 Core；非 dry_run 出 PRE。"""
    created_cores: List[MongoAutofixCore] = []
    dry_run = ctl.is_dry_run()
    for cand in surviving:
        core = _create_core_for_candidate(cand)
        if core is None:
            continue
        created_cores.append(core)
        if dry_run:
            logger.info("mongo autofix dry_run detected ip=%s core=%s", cand.ip, core.id)
            write_autofix_log(MongoAutofixLogEvent.DETECTED, "dry_run: skip PRE ticket", core=core)
            continue
        try:
            ticket = create_autofix_pre_ticket(core)
            if ticket is not None:
                core.pre_ticket_id = ticket.id
                core.deal_status = MongoAutofixStatus.PRE_RUNNING.value
                core.save(update_fields=["pre_ticket_id", "deal_status", "update_at"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("mongo autofix create PRE failed core=%s err=%s", core.id, exc)
            core.deal_status = MongoAutofixStatus.FAIL.value
            core.status_version = str(exc)[:64]
            core.save(update_fields=["deal_status", "status_version", "update_at"])
            write_autofix_log(
                MongoAutofixLogEvent.ERROR,
                f"create PRE failed: {exc}",
                core=core,
            )
    return created_cores


def discover_mongod_backend_faults() -> List[MongoAutofixCore]:
    """
    主发现入口（无 pymongo）：

    1. enable off → return []
    2. 拉 peer member_state；None → skip round
    3. 按 name 聚合旁观者异常；Redis 延迟窗口
    4. 映射 running StorageInstance；按 IP 聚合
    5. 园区熔断 / 重启屏蔽 / 同 RS 限制 / 白名单
    6. 写 MongoAutofixCore；非 dry_run 出 PRE

    Returns:
        本轮新建的 MongoAutofixCore 列表
    """
    if not ctl.is_autofix_enabled():
        logger.info("mongo autofix disabled, skip discover")
        return []

    observations = query_peer_member_states()
    if observations is None:
        logger.error("mongo autofix metrics unavailable, skip round")
        return []

    peer_min = ctl.get_peer_min_count()
    delay_minutes = ctl.get_delay_minutes()
    now_ts = int(time.time())
    # TTL 覆盖延迟窗口 + 余量
    ttl_seconds = max((delay_minutes + 30) * 60, 3600)

    sustained = _collect_sustained_peers(observations, peer_min, delay_minutes, ttl_seconds, now_ts)
    disk_failed = _merge_disk_rw_candidates(sustained, delay_minutes, ttl_seconds, now_ts)

    if not sustained:
        logger.info("mongo autofix no sustained peer/disk faults")
        return []

    storages = _load_running_storages(list(sustained.keys()), enable_configsvr=ctl.is_configsvr_enabled())
    by_ip = _aggregate_by_ip(sustained, storages)
    if not by_ip:
        logger.info("mongo autofix no running storage mapped")
        return []

    for name, val in disk_failed.items():
        parsed = _parse_name(name)
        if not parsed:
            continue
        ip, _port = parsed
        cand = by_ip.get(ip)
        if cand is not None:
            setattr(cand, "_disk_rw_ok", val)

    candidates = _apply_zone_city_gates(list(by_ip.values()))
    candidates = _apply_same_rs_gates(candidates, sustained, by_ip)
    surviving = _filter_restart_shielded(candidates)
    created_cores = _create_cores_and_pre(surviving)

    logger.info("mongo autofix discover done created=%s", len(created_cores))
    return created_cores


# re-export for tests / callers that prefer gates helper living next to discover
__all__ = [
    "discover_mongod_backend_faults",
    "touch_peer_first_seen",
    "clear_peer_first_seen",
    "count_mongo_hosts_by_zone",
]
