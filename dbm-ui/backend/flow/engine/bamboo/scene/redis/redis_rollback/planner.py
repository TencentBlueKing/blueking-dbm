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
import re
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.batches import is_split_round_complete, latest_round_per_shard
from backend.db_services.redis.rollback.constants import (
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
    CACHE_CLUSTER_TYPES,
    SCOPE_CLUSTER,
    SCOPE_INSTANCES,
    SELECT_MODE_BY_IDENTIFY,
    SELECT_MODE_BY_TASK_ID,
    SELECT_MODE_BY_TIME,
    infer_select_mode,
)
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.locator import BackupLocator
from backend.db_services.redis.rollback.shards import (
    ShardRef,
    ShardResolver,
    coverage_gaps,
    overlapping_shards,
    parse_shard_value,
)
from backend.flow.consts import DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    DestHost,
    FullBackupRef,
    KeyFilterSpec,
    RollbackItem,
    RollbackPlan,
)
from backend.flow.utils.redis.redis_cluster_nodes import convert_slot_to_str
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def _parse_dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not value:
        return None
    if isinstance(value, str):
        try:
            return str2datetime(value)
        except Exception:  # pylint: disable=broad-except
            text = value.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    return None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compile_key_regex(pattern: str) -> None:
    if not pattern:
        return
    try:
        re.compile(pattern)
    except re.error as exc:
        raise RollbackPlanError(context={"message": _("key 正则无法编译: {} ({})").format(pattern, exc)})


def normalize_regex_lines(pattern: str) -> str:
    if not pattern:
        return ""
    lines = [line.strip() for line in str(pattern).splitlines() if line.strip()]
    return "\n".join(lines)


class RollbackPlanner:
    """Build a Cache rollback plan: resolve shards, assemble items, check slot layout, pack dest hosts."""

    def __init__(self, cluster: Cluster, info: dict):
        self.cluster = cluster
        self.info = info
        self.resolver = ShardResolver(cluster)
        self.locator = BackupLocator(cluster)

    def build(self, dest_ips: Optional[Sequence[str]] = None, pack: bool = True) -> RollbackPlan:
        if self.cluster.cluster_type not in CACHE_CLUSTER_TYPES:
            raise RollbackPlanError(
                context={
                    "message": _("集群 {} 类型 {} 非 Cache，Phase 1 请改用 REDIS_DATA_STRUCTURE 单据").format(
                        self.cluster.immute_domain, self.cluster.cluster_type
                    )
                }
            )

        select_mode = infer_select_mode(self.info)
        key_filter = KeyFilterSpec.from_ticket(
            normalize_regex_lines(self.info.get("key_white_regex") or ""),
            normalize_regex_lines(self.info.get("key_black_regex") or ""),
        )
        compile_key_regex(key_filter.white_regex)
        compile_key_regex(key_filter.black_regex)

        batch_records, recover_at, backup_identify = self._select_records(select_mode)
        records = self._apply_shard_selection(batch_records)
        if select_mode != SELECT_MODE_BY_TIME:
            recover_at = self._recover_at_from_records(records)

        shard_refs, warnings, shard_keyed = self._resolve_backup_shards(records)
        items = self._build_rollback_items(shard_refs, records)

        batch_shards = {r.get("shard_value") or "" for r in batch_records}
        selected_shards = {item.shard.shard_value for item in items}
        scope = SCOPE_CLUSTER if selected_shards >= batch_shards else SCOPE_INSTANCES

        topology_changed = any(not item.source_is_current for item in items) or any(
            not item.shard.current_master for item in items
        )

        placeholders = self._placeholder_items(batch_records, selected_shards)
        if placeholders:
            warnings.append(
                _("未勾选的分片 {} 将只拉起空实例，保证临时 Proxy 路由完整").format([item.shard.shard_value for item in placeholders])
            )
        items.extend(placeholders)
        warnings.extend(self._check_shard_layout([item.shard.shard_value for item in items]))

        plan = RollbackPlan(
            cluster_id=self.cluster.id,
            immute_domain=self.cluster.immute_domain,
            cluster_type=self.cluster.cluster_type,
            tendis_type=ClusterType.RedisInstance.value,
            bk_cloud_id=self.cluster.bk_cloud_id,
            bk_biz_id=self.cluster.bk_biz_id,
            db_version=self.cluster.major_version,
            proxy_port=self._proxy_port(),
            scope=scope,
            select_mode=select_mode,
            recover_at=recover_at,
            backup_identify=backup_identify,
            locator_source=self.locator.locator_source,
            shard_keyed=shard_keyed,
            topology_changed=topology_changed,
            items=items,
            key_filter=key_filter,
            warnings=warnings,
        )
        if pack:
            dest_ips = list(dest_ips or [])
            if not dest_ips:
                dest_ips = [host["ip"] for host in self.info.get("redis") or [] if host.get("ip")]
            host_count = self._host_count(dest_ips)
            self._pack_dest_hosts(plan, dest_ips, host_count)
        return plan

    def precheck(self, pack: bool = False) -> Dict[str, Any]:
        """Validate every selected shard instead of stopping at the first failure."""
        result: Dict[str, Any] = {"exist": False, "errors": [], "warnings": [], "shards": []}
        try:
            batch_records, _recover_at, _identify = self._select_records(infer_select_mode(self.info))
        except RollbackPlanError as exc:
            result["errors"].append(str(getattr(exc, "message", exc)))
            return result

        selections = self._shard_selections_safe(result["errors"])
        if not selections:
            selections = [
                {"shard_value": shard, "round_key": ""} for shard in sorted(latest_round_per_shard(batch_records))
            ]
        if not selections:
            result["errors"].append(str(_("该批次没有可构造的分片")))
            return result

        by_shard: Dict[str, List[dict]] = defaultdict(list)
        for record in batch_records:
            by_shard[record.get("shard_value") or ""].append(record)
        current_by_shard = {ref.shard_value: ref for ref in self.resolver.from_db_meta() if ref.shard_value}
        needs_routing = self.cluster.cluster_type == ClusterType.TendisTwemproxyRedisInstance.value

        ok_shards: List[str] = []
        for selection in selections:
            detail = self._precheck_shard(selection, by_shard, current_by_shard, needs_routing)
            result["shards"].append(detail)
            if detail["ok"]:
                ok_shards.append(detail["shard_value"])
            if not detail["in_current_topology"]:
                result["warnings"].append(str(_("分片 {} 已不在当前拓扑，将按该批次当时的分片构造").format(detail["shard_value"])))

        conflicts = overlapping_shards(ok_shards)
        if conflicts:
            pairs = ", ".join("{} / {}".format(left, right) for left, right in conflicts)
            result["errors"].append(str(_("所选分片存在重叠: {}").format(pairs)))
        elif needs_routing:
            gaps = coverage_gaps(ok_shards)
            if gaps:
                result["warnings"].append(str(_("本次构造未覆盖全部 slot，产物只含所选分片，缺失: {}").format(convert_slot_to_str(gaps))))

        host_count = int(((self.info.get("resource_spec") or {}).get("redis") or {}).get("count") or 0)
        if host_count and host_count > len(ok_shards):
            result["errors"].append(str(_("主机数量({})不能大于待构造分片数({})").format(host_count, len(ok_shards))))

        result["exist"] = not result["errors"] and all(shard["ok"] for shard in result["shards"])
        return result

    def _shard_selections_safe(self, errors: List[str]) -> List[dict]:
        try:
            return self._shard_selections()
        except RollbackPlanError as exc:
            errors.append(str(getattr(exc, "message", exc)))
            return []

    def _precheck_shard(
        self,
        selection: dict,
        by_shard: Dict[str, List[dict]],
        current_by_shard: dict,
        needs_routing: bool,
    ) -> Dict[str, Any]:
        shard_value = selection["shard_value"]
        round_key = selection["round_key"]
        current = current_by_shard.get(shard_value)
        detail: Dict[str, Any] = {
            "shard_value": shard_value,
            "ok": False,
            "errors": [],
            "round_key": round_key,
            "file_names": [],
            "size": 0,
            "source_ip": "",
            "source_port": 0,
            "source_is_current": False,
            "in_current_topology": current is not None,
        }

        shard_records = by_shard.get(shard_value) or []
        if not shard_records:
            detail["errors"].append(str(_("该批次内分片 {} 没有成功全备").format(shard_value)))
            return detail

        if round_key:
            round_files = [r for r in shard_records if (r.get("round_key") or r.get("file_name")) == round_key]
            if not round_files:
                detail["errors"].append(str(_("分片 {} 在该批次内找不到轮次 {}").format(shard_value, round_key)))
                return detail
        else:
            round_files = latest_round_per_shard(shard_records).get(shard_value) or []
            if not round_files:
                detail["errors"].append(str(_("该批次内分片 {} 没有成功全备").format(shard_value)))
                return detail
            detail["round_key"] = round_files[0].get("round_key") or round_files[0].get("file_name") or ""

        if not is_split_round_complete(round_files):
            detail["errors"].append(str(_("分片 {} 分卷不齐全").format(shard_value)))
        identifies = {f.get("backup_identify") for f in round_files if f.get("backup_identify")}
        if len(identifies) > 1:
            detail["errors"].append(str(_("分片 {} 一轮全备跨 identify: {}").format(shard_value, sorted(identifies))))
        if needs_routing and not parse_shard_value(shard_value).parseable:
            detail["errors"].append(str(_("分片 {} 的 shard_value 无法解析，无法生成临时 Proxy 路由").format(shard_value)))

        source_ip = round_files[0].get("source_ip") or ""
        source_port = int(round_files[0].get("server_port") or 0)
        source = "{}:{}".format(source_ip, source_port)
        detail.update(
            ok=not detail["errors"],
            file_names=[f.get("file_name") or "" for f in round_files],
            size=sum(int(f.get("size") or 0) for f in round_files),
            source_ip=source_ip,
            source_port=source_port,
            source_is_current=(source in {current.current_master, current.current_slave} if current else False),
        )
        return detail

    def _shard_selections(self) -> List[dict]:
        """Normalize ticket ``shards`` into ``[{shard_value, round_key}]``. Empty means whole batch."""
        selections: List[dict] = []
        seen: Set[str] = set()
        for entry in self.info.get("shards") or []:
            if isinstance(entry, str):
                shard_value, round_key = entry, ""
            else:
                shard_value = entry.get("shard_value") or ""
                round_key = entry.get("round_key") or ""
            if not shard_value:
                raise RollbackPlanError(context={"message": _("勾选项缺少 shard_value")})
            if shard_value in seen:
                raise RollbackPlanError(context={"message": _("分片 {} 重复勾选").format(shard_value)})
            seen.add(shard_value)
            selections.append({"shard_value": shard_value, "round_key": round_key})
        return selections

    def _apply_shard_selection(self, records: Sequence[dict]) -> List[dict]:
        """Narrow batch records to the picked (shard, round) pairs.

        No selection means every shard in the batch at its latest round.
        """
        selections = self._shard_selections()
        if not selections:
            return [f for files in latest_round_per_shard(records).values() for f in files]

        by_shard: Dict[str, List[dict]] = defaultdict(list)
        for record in records:
            by_shard[record.get("shard_value") or ""].append(record)

        chosen: List[dict] = []
        for selection in selections:
            shard_value = selection["shard_value"]
            round_key = selection["round_key"]
            shard_records = by_shard.get(shard_value) or []
            if not shard_records:
                raise RollbackPlanError(context={"message": _("该批次内分片 {} 没有成功全备").format(shard_value)})
            if round_key:
                files = [r for r in shard_records if (r.get("round_key") or r.get("file_name")) == round_key]
                if not files:
                    raise RollbackPlanError(
                        context={"message": _("分片 {} 在该批次内找不到轮次 {}").format(shard_value, round_key)}
                    )
            else:
                files = latest_round_per_shard(shard_records).get(shard_value) or []
                if not files:
                    raise RollbackPlanError(context={"message": _("该批次内分片 {} 没有成功全备").format(shard_value)})
            chosen.extend(files)
        return chosen

    def _resolve_backup_shards(self, records: Sequence[dict]) -> tuple:
        """Build shard refs from the selected backup records; current topology is annotation only."""
        if not records:
            raise RollbackPlanError(context={"message": _("没有可构造的分片")})
        if any(not (record.get("shard_value") or "") for record in records):
            raise RollbackPlanError(context={"message": _("备份记录缺少 shard_value，无法按分片构造")})

        refs = self.resolver.from_backup_records(records)
        warnings: List[str] = []
        shard_keyed = True
        for ref in refs:
            if not ref.resolvable:
                shard_keyed = False
                warnings.append(ref.warning or _("分片 {} 无法按 shard_value 解析，降级为 ip:port 匹配").format(ref.shard_value))
            elif not ref.current_master:
                warnings.append(_("分片 {} 已不在当前拓扑，将按该批次当时的分片构造").format(ref.shard_value))
        return refs, warnings, shard_keyed

    def _select_records(self, select_mode: str):
        if select_mode == SELECT_MODE_BY_IDENTIFY:
            identify = self.info.get("backup_identify")
            if not identify:
                raise RollbackPlanError(context={"message": _("by_identify 模式必须提供 backup_identify")})
            records = self.locator.locate_full_by_identify(identify)
            if not records:
                raise RollbackPlanError(context={"message": _("找不到 backup_identify={} 的成功全备").format(identify)})
            recover_at = self._recover_at_from_records(records)
            return records, recover_at, identify

        if select_mode == SELECT_MODE_BY_TASK_ID:
            task_ids = list(self.info.get("backup_task_ids") or [])
            if not task_ids:
                raise RollbackPlanError(context={"message": _("by_task_id 模式必须提供 backup_task_ids")})
            if self.info.get("backup_identify"):
                raise RollbackPlanError(context={"message": _("backup_task_ids 与 backup_identify 互斥")})
            records = self.locator.locate_full_by_task_ids(task_ids)
            found = {r["task_id"] for r in records}
            missing = [tid for tid in task_ids if str(tid) not in found]
            if missing:
                raise RollbackPlanError(context={"message": _("task_id 不属于本集群或未找到: {}").format(missing)})
            identifies = {r.get("backup_identify") for r in records if r.get("backup_identify")}
            if len(identifies) > 1:
                raise RollbackPlanError(context={"message": _("by_task_id 跨 identify: {}").format(sorted(identifies))})
            recover_at = self._recover_at_from_records(records)
            return records, recover_at, next(iter(identifies), "")

        recovery_time_point = self.info.get("recovery_time_point")
        if not recovery_time_point:
            raise RollbackPlanError(context={"message": _("by_time 模式必须提供 recovery_time_point")})
        recover_at = _as_utc(
            str2datetime(recovery_time_point) if isinstance(recovery_time_point, str) else recovery_time_point
        )
        records = self.locator.list_full_in_window(
            start_time=recover_at - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS), end_time=recover_at
        )
        return records, recover_at, ""

    def _recover_at_from_records(self, records: Sequence[dict]) -> datetime:
        explicit = self.info.get("recovery_time_point")
        if explicit:
            return _as_utc(str2datetime(explicit) if isinstance(explicit, str) else explicit)
        ends = [_parse_dt(r.get("backup_end_time") or r.get("uptime")) for r in records]
        ends = [e for e in ends if e]
        if not ends:
            raise RollbackPlanError(context={"message": _("无法从全备记录推导 recover_at")})
        return max(ends)

    def _build_rollback_items(self, shard_refs: Sequence[ShardRef], records: Sequence[dict]) -> List[RollbackItem]:
        """Turn the selected records into one item per shard. Shards come from the backup, not db_meta."""
        current_map = {ref.shard_value: ref for ref in self.resolver.from_db_meta() if ref.shard_value}
        ref_by_shard = {ref.shard_value: ref for ref in shard_refs}

        grouped: Dict[str, List[dict]] = OrderedDict()
        for record in records:
            grouped.setdefault(record.get("shard_value") or "", []).append(record)

        items: List[RollbackItem] = []
        for shard, round_files in grouped.items():
            ref = ref_by_shard.get(shard) or ShardRef(shard_value=shard, resolvable=False)
            if not round_files:
                raise RollbackPlanError(context={"message": _("分片 {} 缺少成功全备").format(shard)})
            if not is_split_round_complete(round_files):
                raise RollbackPlanError(context={"message": _("分片 {} 分卷不齐全").format(shard)})
            identifies = {f.get("backup_identify") for f in round_files if f.get("backup_identify")}
            if len(identifies) > 1:
                raise RollbackPlanError(context={"message": _("分片 {} 一轮全备跨 identify: {}").format(shard, identifies)})
            # One round only: shard selection already collapsed to a single round per shard.
            source_ip = round_files[0].get("source_ip") or ""
            source_port = int(round_files[0].get("server_port") or 0)
            current = current_map.get(shard) or ref
            source = "{}:{}".format(source_ip, source_port)
            source_is_current = source in {current.current_slave, current.current_master}
            full_files = [
                FullBackupRef(
                    task_id=str(f.get("task_id") or ""),
                    file_name=f.get("file_name") or "",
                    size=int(f.get("size") or 0),
                    source_ip=f.get("source_ip") or "",
                    source_port=int(f.get("server_port") or 0),
                    shard_value=shard,
                    backup_identify=f.get("backup_identify") or "",
                    backup_begin_time=f.get("backup_begin_time") or f.get("file_last_mtime") or "",
                    backup_end_time=f.get("backup_end_time") or f.get("uptime") or "",
                    round_key=f.get("round_key") or "",
                )
                for f in round_files
            ]
            items.append(
                RollbackItem(
                    shard=ref,
                    source_ip=source_ip,
                    source_port=source_port,
                    source_is_current=source_is_current,
                    dest_ip="",
                    dest_port=0,
                    full_files=full_files,
                    binlog_files=[],
                )
            )

        return items

    def _placeholder_items(self, batch_records: Sequence[dict], selected_shards: Set[str]) -> List[RollbackItem]:
        """Unselected shards of the batch still get an empty instance.

        Partial rollback would otherwise leave the temp Proxy with segments pointing nowhere,
        making the product unreachable for keys hashing into those slots.
        """
        missing: Dict[str, dict] = OrderedDict()
        for record in batch_records:
            shard = record.get("shard_value") or ""
            if not shard or shard in selected_shards or shard in missing:
                continue
            missing[shard] = record
        if not missing:
            return []

        refs = {ref.shard_value: ref for ref in self.resolver.from_backup_records(missing.values())}
        return [
            RollbackItem(
                shard=refs.get(shard) or ShardRef(shard_value=shard, resolvable=False),
                source_ip=record.get("source_ip") or "",
                source_port=int(record.get("server_port") or 0),
                source_is_current=False,
                dest_ip="",
                dest_port=0,
                full_files=[],
                binlog_files=[],
                is_placeholder=True,
            )
            for shard, record in missing.items()
        ]

    def _check_shard_layout(self, shard_values: Sequence[str]) -> List[str]:
        """Selected shards must not overlap. Partial coverage is allowed and only warns."""
        conflicts = overlapping_shards(shard_values)
        if conflicts:
            pairs = ", ".join("{} / {}".format(left, right) for left, right in conflicts)
            raise RollbackPlanError(context={"message": _("所选分片存在重叠: {}").format(pairs)})

        if self.cluster.cluster_type != ClusterType.TendisTwemproxyRedisInstance.value:
            return []

        unroutable = [value for value in shard_values if not parse_shard_value(value).parseable]
        if unroutable:
            raise RollbackPlanError(
                context={"message": _("分片 {} 的 shard_value 无法解析，无法生成临时 Proxy 路由").format(sorted(unroutable))}
            )

        gaps = coverage_gaps(shard_values)
        if gaps:
            return [_("本次构造未覆盖全部 slot，产物只含所选分片，缺失: {}").format(convert_slot_to_str(gaps))]
        return []

    def _host_count(self, dest_ips: Sequence[str]) -> int:
        if dest_ips:
            return len(dest_ips)
        resource_spec = (self.info.get("resource_spec") or {}).get("redis") or {}
        return int(resource_spec.get("count") or 0)

    def _pack_dest_hosts(self, plan: RollbackPlan, dest_ips: Sequence[str], host_count: int):
        n = len(plan.items)
        m = host_count
        restore_count = sum(1 for item in plan.items if not item.is_placeholder)
        if m <= 0:
            raise RollbackPlanError(context={"message": _("临时机数量必须 > 0")})
        if m > restore_count:
            raise RollbackPlanError(context={"message": _("主机数量({})不能大于待构造分片数({})").format(m, restore_count)})
        if not dest_ips:
            # Ticket-time validation: packing feasibility only.
            return

        # 先摊真实分片再摊空实例，保证每台机器都有实际恢复工作。
        # pack 后 items 变成 dest 分配序（真实分片优先、同源相邻），to_rollback_detail 按此顺序输出。
        items = sorted(plan.items, key=lambda it: (it.is_placeholder, it.source_ip, it.source_port))
        base, remainder = divmod(n, m)
        dest_hosts: List[DestHost] = []
        cursor = 0
        for index, ip in enumerate(dest_ips):
            count = base + 1 if index < remainder else base
            chunk = items[cursor : cursor + count]
            cursor += count
            ports = [DEFAULT_REDIS_START_PORT + offset for offset in range(count)]
            task_ids: List[str] = []
            download_bytes = 0
            for offset, item in enumerate(chunk):
                item.dest_ip = ip
                item.dest_port = ports[offset]
                task_ids.extend(item.task_ids)
                download_bytes += item.download_bytes
            dest_hosts.append(DestHost(ip=ip, ports=ports, task_ids=task_ids, download_bytes=download_bytes))
        plan.items = items
        plan.dest_hosts = dest_hosts

    def _proxy_port(self) -> int:
        proxy = self.cluster.proxyinstance_set.first()
        if proxy:
            return proxy.port
        return DEFAULT_REDIS_START_PORT
