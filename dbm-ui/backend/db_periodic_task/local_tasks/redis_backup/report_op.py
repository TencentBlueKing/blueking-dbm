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
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models.cluster import Cluster
from backend.db_report.enums import ReportStateType
from backend.db_report.models import RedisBackupCheckReport

_STATE_PRIORITY = {
    ReportStateType.NORMAL.value: 0,
    ReportStateType.WARNING.value: 1,
    ReportStateType.ABNORMAL.value: 2,
}


def _compress_port_ranges(ports: list[int]) -> list[tuple[int, int]]:
    """Compress a sorted list of port numbers into (start, end) ranges.

    [30000, 30001, 30002, 30005] -> [(30000, 30002), (30005, 30005)]
    """
    if not ports:
        return []
    sorted_ports = sorted(set(ports))
    ranges: list[tuple[int, int]] = []
    start = end = sorted_ports[0]
    for val in sorted_ports[1:]:
        if val == end + 1:
            end = val
        else:
            ranges.append((start, end))
            start = end = val
    ranges.append((start, end))
    return ranges


def _format_port_ranges(ranges: list[tuple[int, int]]) -> str:
    """Format compressed port ranges for display.

    [(30000, 30002), (30005, 30005)] -> "30000~30002, 30005"
    """
    parts: list[str] = []
    for start, end in ranges:
        parts.append(f"{start}~{end}" if start != end else str(start))
    return ", ".join(parts)


def _group_records_by_ip(records: list[dict]) -> list[dict]:
    """Group records by IP, producing one row per IP with a per-port message breakdown.

    For each IP:
    1. Deduplicate per port -- keep the worst state; collect unique messages.
    2. Group ports that share the same final message.
    3. Format each group as ``port_ranges: msg``.
    4. The row's state is the worst state across all ports on the IP.

    Records with ``instance="all"`` are passed through unchanged.
    """
    # -- pass-through records without ip:port format
    passthrough: list[dict] = []
    # -- per-IP, per-port: {ip: {port: {"state": ..., "msgs": [...]}}}
    ip_ports: dict[str, dict[int, dict]] = defaultdict(dict)

    for record in records:
        instance = record["instance"]
        if IP_PORT_DIVIDER not in instance:
            passthrough.append(record)
            continue

        ip, port_str = instance.rsplit(IP_PORT_DIVIDER, 1)
        try:
            port = int(port_str)
        except ValueError:
            passthrough.append(record)
            continue

        state = record["state"]
        msg = record["msg"]

        if port not in ip_ports[ip]:
            ip_ports[ip][port] = {"state": state, "msgs": [msg]}
        else:
            existing = ip_ports[ip][port]
            if _STATE_PRIORITY.get(state, 0) > _STATE_PRIORITY.get(existing["state"], 0):
                existing["state"] = state
            if msg not in existing["msgs"]:
                existing["msgs"].append(msg)

    result: list[dict] = list(passthrough)

    for ip, ports_map in ip_ports.items():
        worst_state = ReportStateType.NORMAL.value
        # group ports by their joined message string
        msg_to_ports: dict[str, list[int]] = defaultdict(list)
        for port, info in ports_map.items():
            if _STATE_PRIORITY.get(info["state"], 0) > _STATE_PRIORITY.get(worst_state, 0):
                worst_state = info["state"]
            joined_msg = "; ".join(info["msgs"])
            msg_to_ports[joined_msg].append(port)

        # build per-group segments: "(port_ranges): msg"
        segments: list[str] = []
        for msg, ports in msg_to_ports.items():
            port_str = _format_port_ranges(_compress_port_ranges(sorted(ports)))
            segments.append(f"{port_str}: {msg}")

        result.append(
            {
                "instance": ip,
                "state": worst_state,
                "msg": "; ".join(segments),
            }
        )

    return result


class RedisBackupClusterReport:
    """Per-cluster report builder for backup checks.

    Collects per-instance results and produces RedisBackupCheckReport rows
    with proper state / failed_days.
    """

    def __init__(self, cluster: Cluster, subtype: str):
        self.cluster = cluster
        self.subtype = subtype
        self.records: dict[str, list[dict]] = {
            ReportStateType.NORMAL.value: [],
            ReportStateType.WARNING.value: [],
            ReportStateType.ABNORMAL.value: [],
        }

    def append(self, state: str, instance: str, msg: str):
        self.records[state].append({"instance": instance, "state": state, "msg": msg})

    def _make_row(self, *, instance: str, status: bool, state: str, msg: str) -> RedisBackupCheckReport:
        return RedisBackupCheckReport(
            creator="",
            subtype=self.subtype,
            bk_biz_id=self.cluster.bk_biz_id,
            bk_cloud_id=self.cluster.bk_cloud_id,
            cluster=self.cluster.immute_domain,
            cluster_type=self.cluster.cluster_type,
            instance=instance,
            status=status,
            state=state,
            msg=msg,
            failed_days=0,
        )

    def make_skip_record(self, reason: str) -> list[RedisBackupCheckReport]:
        return [self._make_row(instance="all", status=True, state=ReportStateType.NORMAL.value, msg=reason)]

    def make_error_record(self, reason: str) -> list[RedisBackupCheckReport]:
        return [self._make_row(instance="all", status=False, state=ReportStateType.ABNORMAL.value, msg=reason)]

    def make_records(self) -> list[RedisBackupCheckReport]:
        normal_num = len(self.records[ReportStateType.NORMAL.value])
        abnormal_num = len(self.records[ReportStateType.ABNORMAL.value])
        warning_num = len(self.records[ReportStateType.WARNING.value])
        total_num = normal_num + abnormal_num + warning_num

        if total_num == 0:
            return [
                self._make_row(
                    instance="all",
                    status=False,
                    state=ReportStateType.ABNORMAL.value,
                    msg="no instance to check",
                )
            ]

        if abnormal_num == 0 and warning_num == 0:
            return [
                self._make_row(
                    instance="all",
                    status=True,
                    state=ReportStateType.NORMAL.value,
                    msg=f"{total_num} instances checked, all normal",
                )
            ]

        all_records: list[dict] = []
        for state_records in self.records.values():
            all_records.extend(state_records)

        rows: list[RedisBackupCheckReport] = []
        for record in _group_records_by_ip(all_records):
            is_ok = record["state"] == ReportStateType.NORMAL.value
            rows.append(
                self._make_row(
                    instance=record["instance"],
                    status=is_ok,
                    state=record["state"],
                    msg=record["msg"],
                )
            )
        rows.sort(key=lambda r: _STATE_PRIORITY.get(r.state, 0), reverse=True)
        return rows


class RedisBackupCheckBatchOps:
    """Batch operations for RedisBackupCheckReport with failed_days computation."""

    def __init__(self, sub_type: str):
        self.sub_type = sub_type
        self.records: list[RedisBackupCheckReport] = []

    def append(self, record: RedisBackupCheckReport):
        self.records.append(record)

    def bulk_create(self):
        if not self.records:
            return
        self._fill_failed_days()
        RedisBackupCheckReport.objects.bulk_create(self.records)
        self.records = []

    def _fill_failed_days(self):
        prev_days = self._get_continuous_days()
        for record in self.records:
            key = self._continuous_key(record)
            if record.state == ReportStateType.NORMAL.value:
                record.failed_days = 0
            else:
                record.failed_days = prev_days.get(key, 0) + 1

    @staticmethod
    def _continuous_key(row: RedisBackupCheckReport) -> str:
        return f"{row.cluster}:{row.instance}:{row.state}"

    def _get_continuous_days(self) -> dict[str, int]:
        clusters = {r.cluster for r in self.records}
        local_now = timezone.localtime()
        yesterday_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        rows = RedisBackupCheckReport.objects.filter(
            cluster__in=list(clusters),
            subtype=self.sub_type,
            create_at__gte=yesterday_start,
            create_at__lt=yesterday_end,
        )
        result: dict[str, int] = defaultdict(int)
        for row in rows:
            result[self._continuous_key(row)] = row.failed_days
        return result

    def delete_old_records(self, days: int = 360) -> int:
        deleted_count, _ = RedisBackupCheckReport.objects.filter(
            create_at__lte=timezone.now() - timedelta(days=days),
            subtype=self.sub_type,
        ).delete()
        return deleted_count

    def delete_today_records(self) -> int:
        local_now = timezone.localtime()
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        deleted_count, _ = RedisBackupCheckReport.objects.filter(
            create_at__gte=today_start,
            create_at__lt=tomorrow_start,
            subtype=self.sub_type,
        ).delete()
        return deleted_count
