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

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.utils.time import datetime2str

ISSUE_FULL_MISSING = "full_missing"
ISSUE_FULL_UNAVAILABLE = "full_unavailable"
ISSUE_BEFORE_FULL = "before_full"
ISSUE_BINLOG_NOT_UPLOADED = "binlog_not_uploaded"
ISSUE_BINLOG_HEAD_MISSING = "binlog_head_missing"
ISSUE_BINLOG_TOO_FEW = "binlog_too_few"
ISSUE_BINLOG_DUPLICATE = "binlog_duplicate"
ISSUE_BINLOG_GAP = "binlog_gap"
ISSUE_KVSTORE_MISMATCH = "kvstore_mismatch"
ISSUE_UNROUTABLE = "unroutable"
ISSUE_OTHER = "other"

# Summary order: the reason the user has to act on first comes first.
ISSUE_ORDER = (
    ISSUE_FULL_MISSING,
    ISSUE_FULL_UNAVAILABLE,
    ISSUE_BEFORE_FULL,
    ISSUE_BINLOG_NOT_UPLOADED,
    ISSUE_BINLOG_HEAD_MISSING,
    ISSUE_BINLOG_TOO_FEW,
    ISSUE_BINLOG_DUPLICATE,
    ISSUE_BINLOG_GAP,
    ISSUE_KVSTORE_MISMATCH,
    ISSUE_UNROUTABLE,
    ISSUE_OTHER,
)
# The top line names this many reasons; the rest get their own lines.
TOP_LINE_REASONS = 2
INDEX_RANGE_LIMIT = 3
# Sub-reasons of one group named before falling back to the group's generic reason.
DISTINCT_REASON_LIMIT = 3


@dataclass
class ShardIssue:
    """One reason a shard cannot be built. ``message`` is the full text, ``data`` what the summary is made from."""

    code: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


def issue_of(exc: RollbackPlanError, default_code: str = ISSUE_OTHER) -> ShardIssue:
    message = str(getattr(exc, "message", None) or _("回档计划校验失败"))
    return ShardIssue(getattr(exc, "issue_code", "") or default_code, message, dict(getattr(exc, "issue_data", {})))


def chain_data(binlogs: Sequence[Dict]) -> Dict[str, Any]:
    """Index range and newest begin time of the binlogs found, for messages that say what there is."""
    if not binlogs:
        return {"first": None, "last": None, "latest_begin": None}
    ordered = sorted(binlogs, key=lambda b: (b["index"], b["file_name"]))
    return {
        "first": {"index": ordered[0]["index"], "begin_time": ordered[0]["begin_time"]},
        "last": {"index": ordered[-1]["index"], "begin_time": ordered[-1]["begin_time"]},
        "latest_begin": max(b["begin_time"] for b in binlogs),
    }


def index_ranges(indexes: Sequence[int], limit: int = INDEX_RANGE_LIMIT, total: Optional[int] = None) -> str:
    """``#31-33,#40``; past ``limit`` runs, ``#31-33,#40,#45 等12个``."""
    runs: List[List[int]] = []
    for index in sorted(set(indexes)):
        if runs and index == runs[-1][1] + 1:
            runs[-1][1] = index
        else:
            runs.append([index, index])
    text = ",".join("#{}".format(a) if a == b else "#{}-{}".format(a, b) for a, b in runs[:limit])
    count = total if total is not None else len(set(indexes))
    if len(runs) > limit or count > sum(b - a + 1 for a, b in runs):
        text += str(_(" 等{}个")).format(count)
    return text


def kvstore_ranges(kvstores: Sequence[int]) -> str:
    """``kv0-2,kv5``."""
    runs: List[List[int]] = []
    for kvstore in sorted(set(kvstores)):
        if runs and kvstore == runs[-1][1] + 1:
            runs[-1][1] = kvstore
        else:
            runs.append([kvstore, kvstore])
    return ",".join("kv{}".format(a) if a == b else "kv{}-{}".format(a, b) for a, b in runs)


def short_time(dt: Optional[datetime], ref: Optional[datetime] = None, seconds: bool = False) -> str:
    """Platform time zone; the date only when it is not ``ref``'s day."""
    if dt is None:
        return "-"
    local = timezone.localtime(dt)
    text = local.strftime("%H:%M:%S" if seconds else "%H:%M")
    if ref is None or timezone.localtime(ref).date() != local.date():
        text = local.strftime("%m-%d ") + text
    return text


@dataclass
class _Entry:
    shard_value: str
    source_ip: str
    source_port: int
    issue: ShardIssue


def _group(entries: Sequence[_Entry]) -> "OrderedDict[str, List[_Entry]]":
    by_code: Dict[str, List[_Entry]] = {}
    for entry in entries:
        code = entry.issue.code if entry.issue.code in ISSUE_ORDER else ISSUE_OTHER
        by_code.setdefault(code, []).append(entry)
    return OrderedDict((code, by_code[code]) for code in ISSUE_ORDER if code in by_code)


def _shards(entries: Sequence[_Entry]) -> List[str]:
    return list(dict.fromkeys(entry.shard_value for entry in entries))


def _kv_prefix(entries: Sequence[_Entry]) -> str:
    kvstores = [entry.issue.data["kvstore"] for entry in entries if entry.issue.data.get("kvstore") is not None]
    return kvstore_ranges(kvstores) + " " if kvstores else ""


def _chain_text(entries: Sequence[_Entry]) -> str:
    """``#25~#70`` when every entry saw the same range, so one range describes them all."""
    ends = {
        ((entry.issue.data.get("first") or {}).get("index"), (entry.issue.data.get("last") or {}).get("index"))
        for entry in entries
    }
    if len(ends) != 1:
        return ""
    first, last = ends.pop()
    return "" if first is None else "#{}~#{}".format(first, last)


def _reason(code: str, entries: Sequence[_Entry], recover_at: Optional[datetime]) -> Tuple[str, str]:
    """``(reason, hint)`` of one group; the hint is dropped when several reasons share the top line."""
    data = [entry.issue.data for entry in entries]
    single = len(_shards(entries)) == 1
    if code == ISSUE_BEFORE_FULL:
        full_end = max(d["full_end"] for d in data)
        bound = short_time(full_end, recover_at, seconds=True)
        return (
            str(_("回档时刻 {} 早于全备完成（最晚 {}）")).format(short_time(recover_at, recover_at), bound),
            str(_("请选不早于 {} 的时刻")).format(bound),
        )
    if code == ISSUE_BINLOG_NOT_UPLOADED:
        latest = [d["latest_begin"] for d in data if d.get("latest_begin")]
        bound = short_time(min(latest), recover_at, seconds=True) if latest else ""
        chain = _chain_text(entries) if single else ""
        detail = "，".join(part for part in (chain, str(_("最新 {}")).format(bound) if bound else "") if part)
        reason = str(_("{}{} 之后还没有 binlog")).format(_kv_prefix(entries), short_time(recover_at, recover_at))
        if detail:
            reason += "（{}）".format(detail)
        hint = str(_("请选不晚于 {} 或稍后重试")).format(bound) if bound else str(_("请稍后重试"))
        return reason, hint
    if code == ISSUE_BINLOG_HEAD_MISSING:
        reason = str(_("{}全备开始 {} 前没有 binlog")).format(
            _kv_prefix(entries), short_time(min(d["full_start"] for d in data), recover_at)
        )
        firsts = [d["first"] for d in data if d.get("first")]
        if single and firsts:
            first = min(firsts, key=lambda f: f["index"])
            reason += str(_("（最早 #{} {}）")).format(first["index"], short_time(first["begin_time"], recover_at, True))
        return reason, ""
    if code in (ISSUE_BINLOG_GAP, ISSUE_BINLOG_DUPLICATE):
        restarted = any(d.get("restarted") for d in data)
        if single:
            indexes = [index for d in data for index in d.get("missing") or d.get("duplicated") or []]
            total = sum(int(d.get("missing_count") or len(d.get("duplicated") or [])) for d in data)
            ranges = index_ranges(indexes, total=total)
            chain = _chain_text(entries)
            if code == ISSUE_BINLOG_DUPLICATE:
                reason = str(_("{}binlog 序号重复 {}")).format(_kv_prefix(entries), ranges)
            elif restarted:
                reason = str(_("{}binlog 序号回退（实例可能重启过），缺 {}")).format(_kv_prefix(entries), ranges)
            else:
                reason = str(_("{}binlog 缺 {}")).format(_kv_prefix(entries), ranges)
            if chain:
                reason += "（{}）".format(chain)
        else:
            reason = str(_("binlog 序号重复")) if code == ISSUE_BINLOG_DUPLICATE else str(_("binlog 不连续"))
        hint = ""
        if code == ISSUE_BINLOG_GAP and not restarted:
            hint = str(_("可开启“允许 binlog 不连续”"))
        return reason, hint
    if code == ISSUE_BINLOG_TOO_FEW:
        return str(_("{}binlog 少于 2 个")).format(_kv_prefix(entries)), ""
    if code == ISSUE_KVSTORE_MISMATCH:
        return str(_("源实例 kvstore 多于临时实例")), ""
    if code in (ISSUE_FULL_MISSING, ISSUE_UNROUTABLE):
        reasons = list(dict.fromkeys(str(d["reason"]) for d in data if d.get("reason")))
        if 0 < len(reasons) <= DISTINCT_REASON_LIMIT:
            return "、".join(reasons), ""
        return (str(_("批次内没有可用全备")) if code == ISSUE_FULL_MISSING else str(_("shard_value 无法解析"))), ""
    if code == ISSUE_FULL_UNAVAILABLE:
        return str(_("全备已过期或不可下载")), ""
    return entries[0].issue.message, ""


def _who(entries: Sequence[_Entry], unit: bool = True) -> str:
    shards = _shards(entries)
    if len(shards) == 1:
        return str(_("分片 {}")).format(shards[0])
    return str(_("{} 个分片")).format(len(shards)) if unit else str(_("{} 个")).format(len(shards))


def _line(reason: str, hint: str) -> str:
    return "{}，{}".format(reason, hint) if hint else reason


def _jsonable(value):
    if isinstance(value, datetime):
        return datetime2str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


class IssueSummary:
    """Shard issues grouped by reason, rendered as the precheck ``errors`` and ``error_groups``."""

    def __init__(self, entries: Sequence[_Entry], recover_at: Optional[datetime]):
        self.groups = _group(entries)
        self.recover_at = recover_at

    @classmethod
    def of(cls, shards: Sequence[Any], recover_at: Optional[datetime]) -> "IssueSummary":
        entries = [
            _Entry(shard.shard_value, shard.source_ip, shard.source_port, issue)
            for shard in shards
            for issue in shard.issues
        ]
        return cls(entries, recover_at)

    def lines(self) -> List[str]:
        """Top line first, then one line per reason once there is more than one."""
        if not self.groups:
            return []
        reasons = [(code, entries, _reason(code, entries, self.recover_at)) for code, entries in self.groups.items()]
        per_reason = ["{}：{}".format(_who(entries), _line(*reason)) for _code, entries, reason in reasons]
        if len(reasons) == 1:
            return per_reason
        failed = _shards([entry for entries in self.groups.values() for entry in entries])
        top = str(_("{} 个分片无法构造：{}")).format(
            len(failed),
            "；".join(
                "{} {}".format(_who(entries, unit=False), reason[0])
                for _code, entries, reason in reasons[:TOP_LINE_REASONS]
            ),
        )
        return [top] + per_reason

    def error_groups(self) -> List[Dict[str, Any]]:
        groups = []
        for code, entries in self.groups.items():
            reason = _reason(code, entries, self.recover_at)
            groups.append(
                {
                    "code": code,
                    "summary": "{}：{}".format(_who(entries), _line(*reason)),
                    "shards": [
                        {
                            "shard_value": entry.shard_value,
                            "source_ip": entry.source_ip,
                            "source_port": entry.source_port,
                            "kvstore": entry.issue.data.get("kvstore"),
                            "message": entry.issue.message,
                            "data": _jsonable(entry.issue.data),
                        }
                        for entry in entries
                    ],
                }
            )
        return groups
