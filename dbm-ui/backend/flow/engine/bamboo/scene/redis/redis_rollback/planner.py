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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.backup_presence import confirm_backup_tasks
from backend.db_services.redis.rollback.batches import is_split_round_complete, latest_round_per_shard
from backend.db_services.redis.rollback.constants import (
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
    CACHE_CLUSTER_TYPES,
    SCOPE_CLUSTER,
    SCOPE_INSTANCES,
    SELECT_MODE_BY_IDENTIFY,
    SELECT_MODE_BY_TASK_ID,
    SELECT_MODE_BY_TIME,
    UNPACK_RATIO,
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


def _message_of(exc: RollbackPlanError, default: str = "") -> str:
    return str(getattr(exc, "message", None) or default or _("回档计划校验失败"))


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


def host_count_error(host_count: int, restore_count: int) -> Optional[str]:
    """Ensures host count does not exceed shards to be restored.

    Ticket validation, precheck and packing all route here; the ticket serializer used to
    keep its own copy keyed on ``len(shards)``, which is empty on the whole-cluster path
    and therefore never fired.
    """
    if host_count <= 0:
        return str(_("临时机数量必须 > 0"))
    if host_count > restore_count:
        return str(_("主机数量({})不能大于待构造分片数({})").format(host_count, restore_count))
    return None


@dataclass
class ShardEval:
    """One shard's evaluation. Empty ``errors`` means it can be built."""

    shard_value: str
    ref: ShardRef
    round_key: str = ""
    round_files: List[dict] = field(default_factory=list)
    source_ip: str = ""
    source_port: int = 0
    source_is_current: bool = False
    in_current_topology: bool = False
    is_placeholder: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def task_ids(self) -> List[str]:
        if self.is_placeholder or not self.round_files:
            return []
        ids = [str(f.get("task_id") or "") for f in self.round_files]
        ids.extend(str(task_id) for task_id in (self.round_files[0].get("binlog_task_ids") or []) if task_id)
        return ids


@dataclass
class PlanEval:
    """Result of one evaluation pass: what precheck renders and what build assembles."""

    select_mode: str = ""
    recover_at: Optional[datetime] = None
    backup_identify: str = ""
    key_filter: KeyFilterSpec = field(default_factory=KeyFilterSpec)
    batch_records: List[dict] = field(default_factory=list)
    shards: List[ShardEval] = field(default_factory=list)
    # Unselected shards in batch: started as empty instances to cover slots.
    placeholders: List[ShardEval] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    shard_keyed: bool = True

    @property
    def ok(self) -> bool:
        return not self.errors and all(shard.ok for shard in self.shards)

    @property
    def messages(self) -> List[str]:
        return list(self.errors) + [message for shard in self.shards for message in shard.errors]

    @property
    def restore_count(self) -> int:
        """Shards that actually receive data. Placeholders only hold a slot range."""
        return len([shard for shard in self.shards if shard.ok])


class RollbackPlanner:
    """Evaluate a Cache rollback request once, then render it as a precheck report or a plan.

    ``precheck`` and ``build`` differ only in how they present the same evaluation: the first
    lists every failing shard for the UI, the second raises one exception for ticket
    validation. Keeping two implementations of these rules is what let them disagree — a
    partial selection used to warn about uncovered slots in precheck while build silently
    filled them with placeholders.
    """

    def __init__(self, cluster: Cluster, info: dict):
        self.cluster = cluster
        self.info = info
        self.resolver = ShardResolver(cluster)
        self.locator = BackupLocator(cluster)

    # --- rendering ---------------------------------------------------------------------

    def build(self, dest_ips: Optional[Sequence[str]] = None, pack: bool = True) -> RollbackPlan:
        """Assemble the plan, or raise with every problem found."""
        evaluation = self._evaluate()
        if not evaluation.ok:
            raise RollbackPlanError(context={"message": "; ".join(evaluation.messages)})

        items = [self._to_item(shard) for shard in evaluation.shards]
        items.extend(self._to_item(shard) for shard in evaluation.placeholders)

        batch_shards = {record.get("shard_value") or "" for record in evaluation.batch_records}
        selected_shards = {shard.shard_value for shard in evaluation.shards}
        topology_changed = any(not item.source_is_current for item in items) or any(
            not item.shard.current_master for item in items
        )

        plan = RollbackPlan(
            cluster_id=self.cluster.id,
            immute_domain=self.cluster.immute_domain,
            cluster_type=self.cluster.cluster_type,
            tendis_type=ClusterType.RedisInstance.value,
            bk_cloud_id=self.cluster.bk_cloud_id,
            bk_biz_id=self.cluster.bk_biz_id,
            db_version=self.cluster.major_version,
            proxy_port=self._proxy_port(),
            scope=SCOPE_CLUSTER if selected_shards >= batch_shards else SCOPE_INSTANCES,
            select_mode=evaluation.select_mode,
            recover_at=evaluation.recover_at,
            backup_identify=evaluation.backup_identify,
            locator_source=self.locator.locator_source,
            shard_keyed=evaluation.shard_keyed,
            topology_changed=topology_changed,
            items=items,
            key_filter=evaluation.key_filter,
            warnings=list(evaluation.warnings),
        )
        if pack:
            dest_ips = list(dest_ips or [])
            if not dest_ips:
                dest_ips = [host["ip"] for host in self.info.get("redis") or [] if host.get("ip")]
            self._pack_dest_hosts(plan, dest_ips, self._host_count(dest_ips))
        return plan

    def precheck(self, pack: bool = False) -> Dict[str, Any]:
        """Report every failing shard instead of stopping at the first one.

        Never raises: business problems go into ``errors``, unexpected failures are logged.
        """
        result: Dict[str, Any] = {"exist": False, "errors": [], "warnings": [], "shards": []}
        try:
            evaluation = self._evaluate()
        except Exception:  # pylint: disable=broad-except
            logger.exception("redis rollback precheck failed cluster_id=%s", self.cluster.id)
            result["errors"].append(str(_("回档预检失败，请联系管理员")))
            return result

        result["errors"] = list(evaluation.errors)
        result["warnings"] = list(evaluation.warnings)
        result["shards"] = [self._shard_detail(shard) for shard in evaluation.shards]
        result["exist"] = evaluation.ok
        if not result["exist"]:
            logger.warning(
                "redis rollback precheck cluster_id=%s errors=%s shard_errors=%s",
                self.cluster.id,
                result["errors"],
                [message for shard in evaluation.shards for message in shard.errors],
            )
        return result

    @staticmethod
    def _shard_detail(shard: ShardEval) -> Dict[str, Any]:
        return {
            "shard_value": shard.shard_value,
            "ok": shard.ok,
            "errors": list(shard.errors),
            "round_key": shard.round_key,
            "file_names": [f.get("file_name") or "" for f in shard.round_files],
            "size": sum(int(f.get("size") or 0) for f in shard.round_files),
            "source_ip": shard.source_ip,
            "source_port": shard.source_port,
            "source_is_current": shard.source_is_current,
            "in_current_topology": shard.in_current_topology,
            "task_ids": shard.task_ids,
        }

    @staticmethod
    def _to_item(shard: ShardEval) -> RollbackItem:
        return RollbackItem(
            shard=shard.ref,
            source_ip=shard.source_ip,
            source_port=shard.source_port,
            source_is_current=shard.source_is_current,
            dest_ip="",
            dest_port=0,
            full_files=[
                FullBackupRef(
                    task_id=str(f.get("task_id") or ""),
                    file_name=f.get("file_name") or "",
                    size=int(f.get("size") or 0),
                    source_ip=f.get("source_ip") or "",
                    source_port=int(f.get("server_port") or 0),
                    shard_value=shard.shard_value,
                    backup_identify=f.get("backup_identify") or "",
                    backup_begin_time=f.get("backup_begin_time") or f.get("file_last_mtime") or "",
                    backup_end_time=f.get("backup_end_time") or f.get("uptime") or "",
                    round_key=f.get("round_key") or "",
                )
                for f in shard.round_files
            ],
            binlog_files=[],
            is_placeholder=shard.is_placeholder,
        )

    # --- the single evaluation pass ------------------------------------------------------

    def _evaluate(self) -> PlanEval:
        """Run every gate once, accumulating problems rather than raising on the first."""
        evaluation = PlanEval()
        if self.cluster.cluster_type not in CACHE_CLUSTER_TYPES:
            evaluation.errors.append(
                str(
                    _("集群 {} 类型 {} 非 Cache，Phase 1 请改用 REDIS_DATA_STRUCTURE 单据").format(
                        self.cluster.immute_domain, self.cluster.cluster_type
                    )
                )
            )
            return evaluation

        try:
            evaluation.select_mode = infer_select_mode(self.info)
            evaluation.key_filter = KeyFilterSpec.from_ticket(
                normalize_regex_lines(self.info.get("key_white_regex") or ""),
                normalize_regex_lines(self.info.get("key_black_regex") or ""),
            )
            compile_key_regex(evaluation.key_filter.white_regex)
            compile_key_regex(evaluation.key_filter.black_regex)
            (
                evaluation.batch_records,
                evaluation.recover_at,
                evaluation.backup_identify,
            ) = self._select_records(evaluation.select_mode)
            selections = self._shard_selections()
        except RollbackPlanError as exc:
            evaluation.errors.append(_message_of(exc))
            return evaluation

        if not selections:
            selections = [
                {"shard_value": shard, "round_key": ""}
                for shard in sorted(latest_round_per_shard(evaluation.batch_records))
            ]
        if not selections:
            evaluation.errors.append(str(_("该批次没有可构造的分片")))
            return evaluation

        by_shard: Dict[str, List[dict]] = defaultdict(list)
        for record in evaluation.batch_records:
            by_shard[record.get("shard_value") or ""].append(record)
        # from_backup_records reads db_meta; resolve the whole batch once instead of per shard
        ref_by_shard = {ref.shard_value: ref for ref in self.resolver.from_backup_records(evaluation.batch_records)}
        current_by_shard = {ref.shard_value: ref for ref in self.resolver.from_db_meta() if ref.shard_value}
        needs_routing = self.cluster.cluster_type == ClusterType.TendisTwemproxyRedisInstance.value

        for selection in selections:
            shard = self._evaluate_shard(selection, by_shard, ref_by_shard, current_by_shard, needs_routing)
            evaluation.shards.append(shard)
            if not shard.in_current_topology:
                evaluation.warnings.append(str(_("分片 {} 已不在当前拓扑，将按该批次当时的分片构造").format(shard.shard_value)))
            if not shard.ref.resolvable:
                evaluation.shard_keyed = False
                evaluation.warnings.append(
                    str(shard.ref.warning or _("分片 {} 无法按 shard_value 解析，降级为 ip:port 匹配").format(shard.shard_value))
                )

        evaluation.placeholders = self._evaluate_placeholders(evaluation, ref_by_shard, current_by_shard)
        if evaluation.placeholders:
            evaluation.warnings.append(
                str(
                    _("未勾选的分片 {} 将只拉起空实例，保证临时 Proxy 路由完整").format(
                        [shard.shard_value for shard in evaluation.placeholders]
                    )
                )
            )

        self._confirm_backup_presence(evaluation)
        self._check_layout(evaluation, needs_routing)
        self._check_host_count(evaluation)
        if evaluation.select_mode != SELECT_MODE_BY_TIME:
            self._resolve_recover_at(evaluation)
        return evaluation

    def _evaluate_shard(
        self,
        selection: dict,
        by_shard: Dict[str, List[dict]],
        ref_by_shard: Dict[str, ShardRef],
        current_by_shard: dict,
        needs_routing: bool,
    ) -> ShardEval:
        shard_value = selection["shard_value"]
        current = current_by_shard.get(shard_value)
        shard = ShardEval(
            shard_value=shard_value,
            ref=ref_by_shard.get(shard_value) or ShardRef(shard_value=shard_value, resolvable=False),
            round_key=selection["round_key"],
            in_current_topology=current is not None,
        )
        if not shard_value:
            shard.errors.append(str(_("备份记录缺少 shard_value，无法按分片构造")))
            return shard

        shard_records = by_shard.get(shard_value) or []
        if not shard_records:
            shard.errors.append(str(_("该批次内分片 {} 没有成功全备").format(shard_value)))
            return shard

        if shard.round_key:
            round_files = [r for r in shard_records if (r.get("round_key") or r.get("file_name")) == shard.round_key]
            if not round_files:
                shard.errors.append(str(_("分片 {} 在该批次内找不到轮次 {}").format(shard_value, shard.round_key)))
                return shard
        else:
            round_files = latest_round_per_shard(shard_records).get(shard_value) or []
            if not round_files:
                shard.errors.append(str(_("该批次内分片 {} 没有成功全备").format(shard_value)))
                return shard
            shard.round_key = round_files[0].get("round_key") or round_files[0].get("file_name") or ""

        shard.round_files = round_files
        if not is_split_round_complete(round_files):
            shard.errors.append(str(_("分片 {} 分卷不齐全").format(shard_value)))
        identifies = {f.get("backup_identify") for f in round_files if f.get("backup_identify")}
        if len(identifies) > 1:
            shard.errors.append(str(_("分片 {} 一轮全备跨 identify: {}").format(shard_value, sorted(identifies))))
        if needs_routing and not parse_shard_value(shard_value).parseable:
            shard.errors.append(str(_("分片 {} 的 shard_value 无法解析，无法生成临时 Proxy 路由").format(shard_value)))

        shard.source_ip = round_files[0].get("source_ip") or ""
        shard.source_port = int(round_files[0].get("server_port") or 0)
        source = "{}:{}".format(shard.source_ip, shard.source_port)
        shard.source_is_current = bool(current) and source in {current.current_master, current.current_slave}
        return shard

    def _evaluate_placeholders(
        self, evaluation: PlanEval, ref_by_shard: Dict[str, ShardRef], current_by_shard: dict
    ) -> List[ShardEval]:
        """Unselected shards of the batch still get an empty instance.

        Partial rollback would otherwise leave the temp Proxy with segments pointing nowhere,
        making the product unreachable for keys hashing into those slots.
        """
        selected = {shard.shard_value for shard in evaluation.shards}
        missing: Dict[str, dict] = OrderedDict()
        for record in evaluation.batch_records:
            shard_value = record.get("shard_value") or ""
            if not shard_value or shard_value in selected or shard_value in missing:
                continue
            missing[shard_value] = record
        return [
            ShardEval(
                shard_value=shard_value,
                ref=ref_by_shard.get(shard_value) or ShardRef(shard_value=shard_value, resolvable=False),
                source_ip=record.get("source_ip") or "",
                source_port=int(record.get("server_port") or 0),
                in_current_topology=shard_value in current_by_shard,
                is_placeholder=True,
            )
            for shard_value, record in missing.items()
        ]

    def _confirm_backup_presence(self, evaluation: PlanEval) -> None:
        """Ask the backup system whether the planned files can still be downloaded.

        precheck, ticket validation and flow construction all arrive here through
        ``_evaluate``. Placeholders have no files and are not asked about.
        """
        task_ids_by_shard = {
            shard.shard_value: shard.task_ids for shard in evaluation.shards if shard.ok and shard.task_ids
        }
        try:
            problems = confirm_backup_tasks(task_ids_by_shard)
        except RollbackPlanError as exc:
            message = _message_of(exc, str(_("无法向备份系统确认文件仍在")))
            evaluation.errors.append(message)
            for shard in evaluation.shards:
                if shard.ok:
                    shard.errors.append(message)
            return
        for shard in evaluation.shards:
            shard.errors.extend(problems.get(shard.shard_value) or [])

    def _check_layout(self, evaluation: PlanEval, needs_routing: bool) -> None:
        """Overlap is fatal, partial coverage only warns.

        Placeholders count towards coverage: they hold their slot range with an empty
        instance, so a partial selection still routes completely.
        """
        covered = [shard.shard_value for shard in evaluation.shards if shard.ok]
        covered.extend(shard.shard_value for shard in evaluation.placeholders)
        conflicts = overlapping_shards(covered)
        if conflicts:
            pairs = ", ".join("{} / {}".format(left, right) for left, right in conflicts)
            evaluation.errors.append(str(_("所选分片存在重叠: {}").format(pairs)))
            return
        if not needs_routing:
            return
        gaps = coverage_gaps(covered)
        if gaps:
            evaluation.warnings.append(str(_("本次构造未覆盖全部 slot，产物只含所选分片，缺失: {}").format(convert_slot_to_str(gaps))))

    def _check_host_count(self, evaluation: PlanEval) -> None:
        host_count = self._host_count([])
        if not host_count:
            # precheck may run before a resource spec exists; packing enforces it later
            return
        message = host_count_error(host_count, evaluation.restore_count)
        if message:
            evaluation.errors.append(message)

    def _resolve_recover_at(self, evaluation: PlanEval) -> None:
        """by_identify / by_task_id take the target time from the rounds actually chosen."""
        records = [f for shard in evaluation.shards for f in shard.round_files]
        if not records:
            return
        try:
            evaluation.recover_at = self._recover_at_from_records(records)
        except RollbackPlanError as exc:
            evaluation.errors.append(_message_of(exc))

    # --- inputs ---------------------------------------------------------------------------

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

    # --- packing --------------------------------------------------------------------------

    def _host_count(self, dest_ips: Sequence[str]) -> int:
        if dest_ips:
            return len(dest_ips)
        resource_spec = (self.info.get("resource_spec") or {}).get("redis") or {}
        return int(resource_spec.get("count") or 0)

    def _pack_dest_hosts(self, plan: RollbackPlan, dest_ips: Sequence[str], host_count: int):
        restore_count = sum(1 for item in plan.items if not item.is_placeholder)
        message = host_count_error(host_count, restore_count)
        if message:
            raise RollbackPlanError(context={"message": message})
        if not dest_ips:
            # Ticket-time validation: packing feasibility only.
            return

        # Real shards go largest first to the least-loaded host, so download and restore
        # time is balanced and every host (host_count <= restore_count) gets real work.
        # Placeholders carry no data and only even out port counts.
        buckets: List[List[RollbackItem]] = [[] for _ in dest_ips]
        loads = [0] * len(dest_ips)
        real = sorted(
            (item for item in plan.items if not item.is_placeholder),
            key=lambda it: (-it.download_bytes, it.source_ip, it.source_port),
        )
        for item in real:
            index = min(range(len(dest_ips)), key=lambda i: (loads[i], len(buckets[i]), i))
            buckets[index].append(item)
            loads[index] += item.download_bytes
        for item in (item for item in plan.items if item.is_placeholder):
            index = min(range(len(dest_ips)), key=lambda i: (len(buckets[i]), i))
            buckets[index].append(item)

        items: List[RollbackItem] = []
        dest_hosts: List[DestHost] = []
        for ip, chunk in zip(dest_ips, buckets):
            chunk.sort(key=lambda it: (it.is_placeholder, it.source_ip, it.source_port))
            ports = [DEFAULT_REDIS_START_PORT + offset for offset in range(len(chunk))]
            task_ids: List[str] = []
            for item, port in zip(chunk, ports):
                item.dest_ip = ip
                item.dest_port = port
                task_ids.extend(item.task_ids)
            download_bytes = sum(item.download_bytes for item in chunk)
            dest_hosts.append(
                DestHost(
                    ip=ip,
                    ports=ports,
                    task_ids=task_ids,
                    download_bytes=download_bytes,
                    unpacked_bytes=download_bytes * UNPACK_RATIO,
                )
            )
            items.extend(chunk)
        plan.items = items
        plan.dest_hosts = dest_hosts

    def _proxy_port(self) -> int:
        proxy = self.cluster.proxyinstance_set.first()
        if proxy:
            return proxy.port
        return DEFAULT_REDIS_START_PORT
