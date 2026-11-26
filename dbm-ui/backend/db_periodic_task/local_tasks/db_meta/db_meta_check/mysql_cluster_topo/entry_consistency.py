# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at
https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterType,
    InstancePhase,
    InstanceStatus,
    TenDBClusterSpiderRole,
)
from backend.db_meta.models import Cluster
from backend.db_periodic_task import clb_snapshot
from backend.db_periodic_task.clb_snapshot import ClusterCLBSnapshot
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.models import MetaCheckReport
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.redis.redis_report_utils import calculate_failed_days

logger = logging.getLogger("root")

# 和 Redis 入口巡检同一窗口。24 小时内新鲜，24 到 48 小时预警，超过 48 小时不能用。
CLB_SNAPSHOT_FRESH_SECONDS = 24 * 3600
CLB_SNAPSHOT_OUTDATED_SECONDS = 48 * 3600
_YESTERDAY_MIN_HOURS = 18
_YESTERDAY_MAX_HOURS = 36
_RS_PREVIEW_LIMIT = 8


@dataclass
class EntryFragment:
    entry_type: str
    entry_name: str
    details: List[str] = field(default_factory=list)
    abnormal: bool = False


def _enum_value(value) -> str:
    return getattr(value, "value", value)


def _is_master_entry(entry) -> bool:
    return _enum_value(entry.role) == ClusterEntryRole.MASTER_ENTRY.value


def _is_running_online(instance) -> bool:
    return (
        _enum_value(instance.status) == InstanceStatus.RUNNING.value
        and _enum_value(instance.phase) == InstancePhase.ONLINE.value
    )


_UNSET = object()


def _has_forward_to(entry) -> bool:
    if hasattr(entry, "forward_to_id"):
        return bool(entry.forward_to_id)
    return bool(getattr(entry, "forward_to", None))


def _proxy_ips(cluster) -> Set[str]:
    return {proxy.machine.ip for proxy in cluster.proxyinstance_set.all() if _is_running_online(proxy)}


def _entry_storage_ips(entry) -> Set[str]:
    return {storage.machine.ip for storage in entry.storageinstance_set.all() if _is_running_online(storage)}


def _spider_ips(cluster, role: TenDBClusterSpiderRole) -> Set[str]:
    ips = set()
    for proxy in cluster.proxyinstance_set.all():
        extension = getattr(proxy, "tendbclusterspiderext", None)
        if extension is None or not _is_running_online(proxy):
            continue
        if _enum_value(extension.spider_role) == role.value:
            ips.add(proxy.machine.ip)
    return ips


def _expected_dns_ips(cluster, entry) -> Set[str]:
    if _enum_value(cluster.cluster_type) == ClusterType.TenDBCluster.value:
        role = TenDBClusterSpiderRole.SPIDER_MASTER if _is_master_entry(entry) else TenDBClusterSpiderRole.SPIDER_SLAVE
        return _spider_ips(cluster, role)
    if _is_master_entry(entry):
        return _proxy_ips(cluster)
    return _entry_storage_ips(entry)


def _default_dns_ips(cluster, entry) -> Set[str]:
    rows = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id).get_domain(domain_name=entry.entry)
    return {row["ip"] for row in rows}


def _expected_clb_rs_endpoint_set(clb_entry) -> Set[str]:
    """本条入口下代理的 ip:port，和快照 listener_rs 的单项格式一致。"""
    return {"{}:{}".format(proxy.machine.ip, proxy.port) for proxy in clb_entry.proxyinstance_set.all()}


def _summarize_targets(targets: Set[str]) -> str:
    ordered = sorted(targets)
    if len(ordered) <= _RS_PREVIEW_LIMIT:
        return ", ".join(ordered)
    head = ", ".join(ordered[:_RS_PREVIEW_LIMIT])
    return _("{}，等共 {} 个").format(head, len(ordered))


def _diff_details(expected: Set[str], actual: Set[str]) -> List[str]:
    details = []
    missing = expected - actual
    extra = actual - expected
    if missing:
        details.append(_("缺少: {}").format(_summarize_targets(missing)))
    if extra:
        details.append(_("多出: {}").format(_summarize_targets(extra)))
    return details


def _clb_content_details(entry, snap) -> Tuple[List[str], bool]:
    if snap.meta_error:
        return [_("元数据不完整：{}").format(snap.meta_error)], True
    if not (snap.listener_id or "").strip():
        return [_("元数据不完整：监听器 ID 为空")], True

    details = []
    abnormal = False
    if snap.listener_rs is None:
        if snap.listener_rs_error:
            details.append(_("无法查询后端：{}").format(snap.listener_rs_error))
        else:
            details.append(_("无法查询后端"))
        abnormal = True
    else:
        expected = _expected_clb_rs_endpoint_set(entry)
        actual = {str(item).strip() for item in snap.listener_rs if str(item).strip()}
        if expected != actual:
            details.extend(_diff_details(expected, actual))
            abnormal = True
    if snap.unhealthy_rs:
        details.append(_("不健康: {}").format(", ".join(snap.unhealthy_rs)))
        abnormal = True
    if snap.health_error:
        details.append(_("健康检查失败：{}").format(snap.health_error))
        abnormal = True
    return details, abnormal


def _clb_fragment(entry, snapshot: Optional[ClusterCLBSnapshot]) -> Optional[EntryFragment]:
    if snapshot is None:
        return EntryFragment("clb", entry.entry, [_("快照缺失")], True)

    age_seconds = max(0.0, time.time() - snapshot.checked_at)
    age_hours = int(age_seconds // 3600)
    if age_seconds > CLB_SNAPSHOT_OUTDATED_SECONDS:
        return EntryFragment("clb", entry.entry, [_("快照过旧（{} 小时）").format(age_hours)], True)

    snap = snapshot.entry_by_id(entry.id)
    if snap is None:
        return EntryFragment("clb", entry.entry, [_("快照缺失")], True)

    details, abnormal = _clb_content_details(entry, snap)
    if age_seconds >= CLB_SNAPSHOT_FRESH_SECONDS:
        details.append(_("快照偏旧（{} 小时）").format(age_hours))
    if not details:
        return None
    return EntryFragment("clb", entry.entry, details, abnormal)


def _dns_fragment(cluster, entry, dns_get) -> Optional[EntryFragment]:
    try:
        actual = dns_get(cluster, entry)
    except Exception as exc:
        logger.exception(_("查询域名 {} 解析失败").format(entry.entry))
        return EntryFragment("dns", entry.entry, [_("解析失败：{}").format(exc)], True)

    expected = _expected_dns_ips(cluster, entry)
    if actual == expected:
        return None
    return EntryFragment("dns", entry.entry, _diff_details(expected, actual), True)


def _fragment_line(fragment: EntryFragment) -> str:
    return "{}  ({}): {}".format(fragment.entry_type, fragment.entry_name, "; ".join(fragment.details))


def render_entry_check(fragments: List[EntryFragment]) -> Tuple[str, str]:
    if not fragments:
        return ReportStateType.NORMAL.value, _("全部入口一致")
    abnormal = any(fragment.abnormal for fragment in fragments)
    state = ReportStateType.ABNORMAL.value if abnormal else ReportStateType.WARNING.value
    return state, "; ".join(_fragment_line(fragment) for fragment in fragments)


def build_mysql_entry_check(cluster, snapshot: Optional[ClusterCLBSnapshot], dns_get=None) -> Tuple[str, str]:
    lookup = dns_get or _default_dns_ips
    fragments = []
    for entry in sorted(cluster.clusterentry_set.all(), key=lambda item: item.id):
        entry_type = _enum_value(entry.cluster_entry_type)
        fragment = None
        if entry_type == ClusterEntryType.CLB.value:
            fragment = _clb_fragment(entry, snapshot)
        elif entry_type == ClusterEntryType.DNS.value and not _has_forward_to(entry):
            fragment = _dns_fragment(cluster, entry, lookup)
        if fragment:
            fragments.append(fragment)
    return render_entry_check(fragments)


def _load_cluster(cluster_id: int) -> Cluster:
    return Cluster.objects.prefetch_related(
        "clusterentry_set__proxyinstance_set__machine",
        "clusterentry_set__storageinstance_set__machine",
        "proxyinstance_set__machine",
        "proxyinstance_set__tendbclusterspiderext",
    ).get(id=cluster_id)


def load_clb_snapshots(cluster_ids: List[int]) -> Dict[int, Optional[ClusterCLBSnapshot]]:
    if not cluster_ids:
        return {}
    try:
        return clb_snapshot.get_many(cluster_ids)
    except Exception:
        logger.exception(_("批量读取 {} 个集群的 CLB 快照失败").format(len(cluster_ids)))
        return {}


def _failed_days(cluster, state: str) -> int:
    if state == ReportStateType.NORMAL.value:
        return 0
    now = timezone.now()
    last = (
        MetaCheckReport.objects.filter(
            cluster=cluster.immute_domain,
            subtype=MetaCheckSubType.MysqlEntryInconsistent.value,
            create_at__gte=now - timedelta(hours=_YESTERDAY_MAX_HOURS),
            create_at__lte=now - timedelta(hours=_YESTERDAY_MIN_HOURS),
        )
        .order_by("-create_at")
        .first()
    )
    return calculate_failed_days(state, last)


def write_mysql_entry_report(cluster_id: int, snapshot=_UNSET) -> MetaCheckReport:
    """一个集群写一行访问入口报告。读快照，DNS 当场查。不打名字服务。"""
    cluster = _load_cluster(cluster_id)
    if snapshot is _UNSET:
        try:
            snapshot = clb_snapshot.get_many([cluster.id]).get(cluster.id)
        except Exception:
            logger.exception(_("读取集群 {} 的 CLB 快照失败").format(cluster.immute_domain))
            snapshot = None
    state, msg = build_mysql_entry_check(cluster, snapshot)
    report = MetaCheckReport(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        ip=None,
        port=None,
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        machine_type="",
        subtype=MetaCheckSubType.MysqlEntryInconsistent.value,
        state=state,
        status=state == ReportStateType.NORMAL.value,
        msg=msg,
        failed_days=_failed_days(cluster, state),
        creator="system",
        updater="system",
    )
    report.save()
    return report
