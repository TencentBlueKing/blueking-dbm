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
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from django.utils.translation import gettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.constants import (
    SINGLE_INSTANCE_SHARD_VALUE,
    SWITCHED_SHARD_VALUE,
    TWEMPROXY_SHARD_MIN,
    TWEMPROXY_SHARD_TOTAL,
)

logger = logging.getLogger("flow")

_RANGE_SEPARATOR = re.compile(r"[\s,]+")


@dataclass
class ShardRef:
    shard_value: str
    current_master: Optional[str] = None
    current_slave: Optional[str] = None
    resolvable: bool = True
    warning: str = ""


@dataclass
class ShardParseResult:
    ranges: List[Tuple[int, int]] = field(default_factory=list)
    parseable: bool = True
    reason: str = ""

    @property
    def slots(self) -> List[int]:
        slots: List[int] = []
        for start, end in self.ranges:
            slots.extend(range(start, end + 1))
        return slots


def parse_shard_value(shard_value: str) -> ShardParseResult:
    """Parse a backup/db_meta shard_value into inclusive ranges.

    Supports multi-range values such as ``"1365-1637 10651-10923"``, single
    slots, and ignores migrating/importing markers wrapped in ``[...]``.
    Non-numeric segments (including the literal ``switched-0``) return
    ``parseable=False`` instead of raising.
    """
    raw = "" if shard_value is None else str(shard_value).strip()
    if not raw:
        return ShardParseResult(parseable=False, reason=_("shard_value 为空"))
    if raw == SWITCHED_SHARD_VALUE:
        return ShardParseResult(parseable=False, reason=_("shard_value 为 switched-0，无法参与分片匹配"))

    ranges: List[Tuple[int, int]] = []
    for token in _RANGE_SEPARATOR.split(raw):
        if not token:
            continue
        if token.startswith("[") and token.endswith("]"):
            continue
        parts = token.split("-")
        try:
            if len(parts) == 1:
                start = end = int(parts[0])
            elif len(parts) == 2:
                start, end = int(parts[0]), int(parts[1])
            else:
                return ShardParseResult(parseable=False, reason=_("shard_value 格式不可解析: {}").format(raw))
        except (TypeError, ValueError):
            return ShardParseResult(parseable=False, reason=_("shard_value 含非数字段: {}").format(raw))
        if start > end:
            return ShardParseResult(parseable=False, reason=_("shard_value 范围起止颠倒: {}").format(raw))
        ranges.append((start, end))

    if not ranges:
        return ShardParseResult(parseable=False, reason=_("shard_value 无可解析区间: {}").format(raw))
    return ShardParseResult(ranges=ranges, parseable=True)


def round_key_from_filename(file_name: str) -> str:
    """Group split volumes of the same backup by stripping ``.split.NNN``."""
    name = (file_name or "").split("/")[-1]
    return re.sub(r"\.split\.\d+$", "", name)


def extract_identify_prefix(backup_identify: str) -> str:
    from backend.db_services.redis.rollback.constants import IDENTIFY_PREFIXES, IDENTIFY_UNKNOWN

    identify = backup_identify or ""
    for prefix in IDENTIFY_PREFIXES:
        if identify.startswith(prefix):
            return prefix
    return IDENTIFY_UNKNOWN


def ip_port(ip: str, port: int) -> str:
    return "{}{}{}".format(ip, IP_PORT_DIVIDER, port)


class ShardResolver:
    """Resolve topology-independent shard_value from db_meta or backup records."""

    def __init__(self, cluster: Cluster):
        self.cluster = cluster

    def from_db_meta(self) -> List[ShardRef]:
        refs: List[ShardRef] = []
        for master in self.cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            refs.append(self._ref_from_master(master))
        return refs

    def from_backup_records(self, records: Iterable[dict]) -> List[ShardRef]:
        current = {ref.shard_value: ref for ref in self.from_db_meta() if ref.resolvable and ref.shard_value}
        seen = set()
        refs: List[ShardRef] = []
        for record in records:
            shard_value = record.get("shard_value") or ""
            key = shard_value or "{}:{}".format(record.get("source_ip"), record.get("server_port"))
            if key in seen:
                continue
            seen.add(key)
            current_ref = current.get(shard_value)
            parsed = parse_shard_value(shard_value) if shard_value else ShardParseResult(parseable=False)
            refs.append(
                ShardRef(
                    shard_value=shard_value,
                    current_master=current_ref.current_master if current_ref else None,
                    current_slave=current_ref.current_slave if current_ref else None,
                    resolvable=parsed.parseable,
                    warning="" if parsed.parseable else parsed.reason,
                )
            )
        return refs

    def cluster_shard_map(self) -> List[dict]:
        """Current topology mapping for UI (instance <-> shard)."""
        mapping = []
        for ref in self.from_db_meta():
            mapping.append(
                {
                    "shard_value": ref.shard_value,
                    "current_master": ref.current_master,
                    "current_slave": ref.current_slave,
                    "resolvable": ref.resolvable,
                    "warning": ref.warning,
                }
            )
        return mapping

    def _ref_from_master(self, master) -> ShardRef:
        shard_value = self._master_shard_value(master)
        slave_ipport = None
        try:
            slave = master.as_ejector.get().receiver
            slave_ipport = ip_port(slave.machine.ip, slave.port)
        except Exception:  # pylint: disable=broad-except
            logger.warning("cluster %s master %s has no slave", self.cluster.id, master.ip_port)

        if shard_value == SWITCHED_SHARD_VALUE:
            return ShardRef(
                shard_value=shard_value,
                current_master=ip_port(master.machine.ip, master.port),
                current_slave=slave_ipport,
                resolvable=False,
                warning=_("分片 {} 上报 shard_value=switched-0，降级为 ip:port 匹配").format(
                    ip_port(master.machine.ip, master.port)
                ),
            )
        parsed = parse_shard_value(shard_value)
        if not parsed.parseable:
            return ShardRef(
                shard_value=shard_value,
                current_master=ip_port(master.machine.ip, master.port),
                current_slave=slave_ipport,
                resolvable=False,
                warning=parsed.reason,
            )
        return ShardRef(
            shard_value=shard_value,
            current_master=ip_port(master.machine.ip, master.port),
            current_slave=slave_ipport,
            resolvable=True,
        )

    def _master_shard_value(self, master) -> str:
        if self.cluster.cluster_type == ClusterType.TendisRedisInstance.value:
            return SINGLE_INSTANCE_SHARD_VALUE
        dtl = self.cluster.nosqlstoragesetdtl_set.filter(instance=master).first()
        if dtl and dtl.seg_range:
            return dtl.seg_range
        return ""


def coverage_gaps(
    shard_values: Sequence[str], total: int = TWEMPROXY_SHARD_TOTAL, start: int = TWEMPROXY_SHARD_MIN
) -> List[int]:
    """Return missing slots when covering ``[start, total)``."""
    covered = set()
    for value in shard_values:
        parsed = parse_shard_value(value)
        if not parsed.parseable:
            continue
        covered.update(parsed.slots)
    expected = set(range(start, total))
    return sorted(expected - covered)


def overlapping_shards(shard_values: Sequence[str]) -> List[Tuple[str, str]]:
    """Return pairs of shard_values whose slot ranges intersect.

    Unparseable values (``switched-0`` / empty) are skipped, same as ``coverage_gaps``.
    """
    parsed_ranges: List[Tuple[str, List[Tuple[int, int]]]] = []
    for value in shard_values:
        parsed = parse_shard_value(value)
        if not parsed.parseable:
            continue
        parsed_ranges.append((value, parsed.ranges))

    conflicts: List[Tuple[str, str]] = []
    for index, (left_value, left_ranges) in enumerate(parsed_ranges):
        for right_value, right_ranges in parsed_ranges[index + 1 :]:
            if _ranges_intersect(left_ranges, right_ranges):
                conflicts.append((left_value, right_value))
    return conflicts


def _ranges_intersect(left: Sequence[Tuple[int, int]], right: Sequence[Tuple[int, int]]) -> bool:
    for left_start, left_end in left:
        for right_start, right_end in right:
            if left_start <= right_end and right_start <= left_end:
                return True
    return False
