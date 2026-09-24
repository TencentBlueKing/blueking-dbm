# -*- coding: utf-8 -*-
"""
mongos 故障发现：独立消费 HADB 切换队列，写 MongoAutofixCore 并出 PRE。
不走 Redis AutofixCore / ignore。
"""
import logging
from typing import Dict, List, Optional

from backend.components.hadb.client import HADBApi
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts_biz
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Machine
from backend.db_services.mongodb.autofix import ctl
from backend.db_services.mongodb.autofix.discover import (
    _apply_zone_city_gates,
    _city_name,
    _filter_restart_shielded,
    _record_ignore,
)
from backend.db_services.mongodb.autofix.enums import MongoAutofixCtlItem
from backend.db_services.mongodb.autofix.gates import HostCandidate
from backend.db_services.mongodb.autofix.models import MongoAutofixCtl
from backend.db_services.mongodb.autofix.ticket_create import create_one_mongos_autofix_pre
from backend.db_services.redis.autofix.const import SWITCH_SMALL, RedisSwitchHost
from backend.db_services.redis.autofix.enums import AutofixItem, DBHASwitchResult
from backend.db_services.redis.autofix.models import RedisAutofixCtl
from backend.exceptions import ApiRequestError, ApiResultError
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


def is_mongos_switch_host(host: RedisSwitchHost) -> bool:
    if host.cluster_type != ClusterType.MongoShardedCluster.value:
        return False
    return str(host.instance_type or "").lower() == MachineType.MONGOS.value


def host_switch_all_success(host: RedisSwitchHost) -> bool:
    return (
        len(host.cluster_ports) == len(host.switch_ports)
        and len(host.sw_result) == 1
        and bool(host.sw_result.get(DBHASwitchResult.SUCC.value))
    )


def next_mongos_dbha_cursor(switch_id: int, queues: list, mongos_hosts: List[RedisSwitchHost]) -> int:
    """非 mongos 日志不阻塞游标；未切完的 mongos 停在其 min uid。"""
    if not queues:
        return switch_id
    batch_max = max(int(item["uid"]) for item in queues)
    waiting = [h.sw_min_id for h in mongos_hosts if not host_switch_all_success(h) and h.sw_min_id]
    if waiting:
        return min(waiting)
    return batch_max + 1


def _dbha_cursor_initialized() -> bool:
    return MongoAutofixCtl.objects.filter(ctl_name=MongoAutofixCtlItem.DBHA_ID.value).exists()


def _seed_dbha_cursor() -> int:
    """首次从 Redis 自愈游标对齐，避免回放历史切换日志。"""
    seed = 0
    try:
        redis_ctl = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.DBHA_ID.value).first()
        if redis_ctl and redis_ctl.ctl_value:
            seed = int(redis_ctl.ctl_value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mongo mongos dbha seed from redis fail err=%s", exc)
        seed = 0
    ctl.set_ctl_value(MongoAutofixCtlItem.DBHA_ID.value, str(seed))
    logger.info("mongo mongos dbha cursor seeded=%s", seed)
    return seed


def _load_dbha_cursor() -> int:
    if not _dbha_cursor_initialized():
        return _seed_dbha_cursor()
    try:
        return int(ctl.get_ctl_value(MongoAutofixCtlItem.DBHA_ID.value) or 0)
    except (TypeError, ValueError):
        return 0


def _query_switch_queue(switch_id: int) -> list:
    try:
        queues = HADBApi.switch_queue(params={"name": "query_switch_queue_by_uid", "query_args": {"uid": switch_id}})
    except (ApiResultError, ApiRequestError, Exception) as error:  # pylint: disable=broad-except
        raise Exception("mongo mongos query switch logs fail: {}".format(error))
    return queues or []


def _aggregate_switch_hosts(switch_queues: list) -> Dict[str, RedisSwitchHost]:
    switch_hosts: Dict[str, RedisSwitchHost] = {}
    for switch_inst in switch_queues:
        switch_ip, switch_id = switch_inst["ip"], int(switch_inst["uid"])
        if not switch_hosts.get(switch_ip):
            cluster = query_cluster_by_hosts_biz([switch_ip], int(switch_inst["app"]), int(switch_inst["cloud_id"]))
            if not cluster:
                logger.info("mongo mongos dbha ignore ip=%s, no cluster", switch_ip)
                continue
            one_cluster, all_ports = cluster[0], []
            for cls_obj in cluster:
                all_ports.extend(cls_obj["cs_ports"])
            switch_hosts[switch_ip] = RedisSwitchHost(
                bk_biz_id=one_cluster["bk_biz_id"],
                cluster_id=one_cluster["cluster_id"],
                immute_domain=";".join([cls_obj["cluster"] for cls_obj in cluster]),
                cluster_type=one_cluster["cluster_type"],
                instance_type=one_cluster["instance_role"],
                bk_host_id=one_cluster["bk_host_id"],
                cluster_ports=all_ports,
                ip=switch_ip,
                switch_ports=[],
                sw_max_id=0,
                sw_min_id=SWITCH_SMALL,
                ignore_fix=False,
                sw_result={},
            )
            switch_hosts[switch_ip].bk_cloud_id = one_cluster.get("bk_cloud_id") or int(
                switch_inst.get("cloud_id") or 0
            )
        current_host = switch_hosts[switch_ip]
        current_host.switch_ports.append(switch_inst["port"])
        if not current_host.sw_result.get(switch_inst["status"]):
            current_host.sw_result[switch_inst["status"]] = []
        current_host.sw_result[switch_inst["status"]].append(switch_inst["port"])
        if switch_id > current_host.sw_max_id:
            current_host.sw_max_id = switch_id
        if switch_id < current_host.sw_min_id:
            current_host.sw_min_id = switch_id
    return switch_hosts


def _primary_domain(immute_domain: str) -> str:
    return (immute_domain or "").split(";")[0].strip()


def _host_to_candidate(host: RedisSwitchHost) -> HostCandidate:
    machine = None
    if host.bk_host_id:
        machine = (
            Machine.objects.filter(bk_host_id=host.bk_host_id)
            .select_related("bk_city", "bk_city__logical_city")
            .first()
        )
    if machine is None:
        machine = (
            Machine.objects.filter(ip=host.ip, bk_biz_id=host.bk_biz_id)
            .select_related("bk_city", "bk_city__logical_city")
            .first()
        )
    cand = HostCandidate(
        ip=host.ip,
        bk_host_id=host.bk_host_id,
        bk_sub_zone_id=(machine.bk_sub_zone_id if machine else 0) or 0,
        bk_city=_city_name(machine) if machine else "",
        cluster_ids=[host.cluster_id] if host.cluster_id else [],
        names={f"{host.ip}:{port}" for port in (host.cluster_ports or [])} or {host.ip},
    )
    setattr(cand, "_switch_host", host)
    return cand


def apply_mongos_mongo_ignore(hosts: List[RedisSwitchHost]) -> List[RedisSwitchHost]:
    """套 Mongo 自愈 ignore：白名单 / 园区城市熔断 / 重启单据屏蔽。不走 Redis ignore。"""
    passed: List[RedisSwitchHost] = []
    candidates: List[HostCandidate] = []
    for host in hosts:
        domain = _primary_domain(host.immute_domain)
        if not ctl.is_whitelist_allowed(host.bk_biz_id, domain):
            _record_ignore(
                bk_cloud_id=int(getattr(host, "bk_cloud_id", 0) or 0),
                bk_biz_id=host.bk_biz_id,
                cluster_id=host.cluster_id,
                cluster_type=host.cluster_type,
                immute_domain=domain,
                bk_host_id=host.bk_host_id,
                ip=host.ip,
                ignore_msg="not_in_whitelist",
            )
            logger.info("mongo mongos ignore whitelist ip=%s domain=%s", host.ip, domain)
            continue
        candidates.append(_host_to_candidate(host))

    candidates = _apply_zone_city_gates(candidates)
    candidates = _filter_restart_shielded(candidates)
    for cand in candidates:
        host = getattr(cand, "_switch_host", None)
        if host:
            passed.append(host)
    return passed


def discover_mongos_dbha_faults() -> List[Ticket]:
    """
    消费 HADB 切换队列中的 mongos，整机切成功后出 PRE。
    ignore 用 Mongo 自愈闸门（白名单 / 园区城市 / 重启屏蔽），不用 Redis ignore。
    """
    if not ctl.is_autofix_enabled():
        logger.info("mongo autofix disabled, skip mongos dbha discover")
        return []

    if not _dbha_cursor_initialized():
        _seed_dbha_cursor()
        logger.info("mongo mongos dbha cursor seeded, skip this round")
        return []

    switch_id = _load_dbha_cursor()
    queues = _query_switch_queue(switch_id)
    if not queues:
        return []

    hosts = _aggregate_switch_hosts(queues)
    mongos_hosts = [h for h in hosts.values() if is_mongos_switch_host(h)]
    next_id = next_mongos_dbha_cursor(switch_id, queues, mongos_hosts)
    ctl.set_ctl_value(MongoAutofixCtlItem.DBHA_ID.value, str(next_id))

    tickets: List[Optional[Ticket]] = []
    ready: List[RedisSwitchHost] = []
    for host in mongos_hosts:
        if not host_switch_all_success(host):
            logger.info(
                "mongo mongos dbha wait switch ip=%s ports=%s result=%s",
                host.ip,
                host.switch_ports,
                host.sw_result,
            )
            continue
        ready.append(host)
    ready = apply_mongos_mongo_ignore(ready)
    for host in ready:
        ticket = create_one_mongos_autofix_pre(
            ip=host.ip,
            bk_host_id=host.bk_host_id,
            bk_biz_id=host.bk_biz_id,
            bk_cloud_id=int(getattr(host, "bk_cloud_id", 0) or 0),
            cluster_id=host.cluster_id,
            cluster_type=host.cluster_type,
            immute_domain=host.immute_domain,
        )
        if ticket:
            tickets.append(ticket)
    created = [t for t in tickets if t]
    logger.info("mongo mongos dbha discover created=%s next_id=%s", len(created), next_id)
    return created
