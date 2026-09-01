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
from datetime import datetime, timedelta
from typing import Optional, TypedDict

from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.redis_tasks.agent_checks.config import RedisAgentCheckConfig
from backend.db_report.enums import ReportStateType
from backend.db_report.models import RedisCheckReport
from backend.dbm_aiagent.tasks.base import AITask
from backend.dbm_aiagent.tasks.invoker import AgentRequest
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord

logger = logging.getLogger("root")

REDIS_EXCLUSIVE_TICKET_TYPES = [
    TicketType.REDIS_DTS_ONLINE_SWITCH.value,
    TicketType.REDIS_MASTER_SLAVE_SWITCH.value,
    TicketType.REDIS_CLUSTER_CUTOFF.value,
    TicketType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
    TicketType.REDIS_CLUSTER_TYPE_UPDATE.value,
    TicketType.REDIS_CLUSTER_REINSTALL_DBMON.value,
]

TICKET_RUNNING_STATUS_VALUES = [s.value for s in TICKET_RUNNING_STATUS_SET]
PRIORITY_ALARM_MAX_PAGES = 50
REDIS_ALARM_LABEL = "DBM_REDIS"


class RedisClusterItem(TypedDict):
    cluster_id: int
    cluster_domain: str


class RedisAgentCheckTask(AITask):
    """Redis cluster consumer for agent checks."""

    config_cls = RedisAgentCheckConfig
    subtype = None
    prompt_template: str = "cluster_domains: [{cluster_domain}]"

    def work_item_id(self, item) -> str:
        cluster_id = item.get("cluster_id") if isinstance(item, dict) else item
        return f"cluster:{cluster_id}"

    def work_item_data(self, item) -> dict:
        if isinstance(item, dict):
            return {k: v for k, v in item.items() if k != "cluster"}
        return {"cluster_id": item}

    def build_request(self, item, *, overrides=None) -> AgentRequest:
        overrides = overrides or {}
        domain = ""
        if isinstance(item, dict):
            domain = item.get("cluster_domain") or ""
            cluster = item.get("cluster")
            if not domain and cluster is not None:
                domain = cluster.immute_domain
        if not domain:
            cluster_id = item.get("cluster_id") if isinstance(item, dict) else item
            cluster = Cluster.objects.filter(id=cluster_id).first()
            domain = cluster.immute_domain if cluster else str(cluster_id)
        template = overrides.get("prompt_template", self.prompt_template)
        return AgentRequest(content=template.format(cluster_domain=domain))

    def on_before_execute(self, item) -> Optional[str]:
        """Re-check only state that may change while a job waits in the queue."""
        if isinstance(item, dict):
            cluster_id = item.get("cluster_id")
            cluster = item.get("cluster")
        else:
            cluster_id = item
            cluster = None
        if cluster is None:
            cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            return "cluster not found"
        if cluster.phase != ClusterPhase.ONLINE.value:
            return f"cluster phase={cluster.phase} is not online"

        cutoff = timezone.now() - timedelta(days=self.config.lookback_days)
        has_recent = (
            ClusterOperateRecord.objects.filter(
                cluster_id=cluster.id,
                ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
            )
            .filter(Q(ticket__create_at__gte=cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
            .exists()
        )
        if has_recent:
            return "recent or active capacity/autofix/migrate ticket"
        return None


class RedisClusterSelector:
    """Producer-side full-cluster selection for Redis agent checks."""

    def __init__(self, config: RedisAgentCheckConfig, subtype, *, task_key: str = ""):
        self.config = config
        self.subtype = subtype
        self.task_key = task_key

    def _build_recently_checked_ids(self, now: datetime) -> set[int]:
        if self.config.recent_check_mode == "calendar_day":
            report_day = int(now.strftime("%Y%m%d"))
            return set(
                RedisCheckReport.objects.filter(
                    subtype=self.subtype.value,
                    report_day=report_day,
                ).values_list("cluster_id", flat=True)
            )
        return set(
            RedisCheckReport.objects.filter(
                subtype=self.subtype.value,
                create_at__gte=now - timedelta(hours=24),
            ).values_list("cluster_id", flat=True)
        )

    @staticmethod
    def _extract_cluster_domain_from_alert_tags(tags) -> str:
        if isinstance(tags, dict):
            return tags.get("cluster_domain", "")
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict) and tag.get("key") == "cluster_domain":
                    return tag.get("value", "")
        return ""

    def _build_alarm_query_string(self, alarm_name_set: set[str]) -> str:
        base_query = f'labels: "{REDIS_ALARM_LABEL}"'
        if not self.config.priority_alarm_request_name_filter:
            return base_query
        if not alarm_name_set:
            return base_query
        name_filter = " OR ".join(f'strategy_name: "{name}"' for name in sorted(alarm_name_set))
        return f"{base_query} AND ({name_filter})"

    def _pull_priority_alarm_cluster_domains(self, now: datetime, *, limit: int) -> list[str]:
        if limit <= 0:
            return []
        alarm_name_set = {
            name.strip() for name in self.config.priority_alarm_names if isinstance(name, str) and name.strip()
        }
        if not alarm_name_set:
            return []

        lookback_hours = max(1, int(self.config.priority_alarm_lookback_hours))
        start_time = now - timedelta(hours=lookback_hours)
        query_param = {
            "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
            "start_time": int(start_time.timestamp()),
            "end_time": int(now.timestamp()),
            "page": 1,
            "page_size": 200,
            "status": ["ABNORMAL"],
            "show_aggs": False,
            "show_overview": False,
            "query_string": self._build_alarm_query_string(alarm_name_set),
        }

        fetched = 0
        ordered_domains: list[str] = []
        seen_domains: set[str] = set()
        while len(ordered_domains) < limit:
            data = BKMonitorV3Api.search_alert(query_param)
            page_alerts = data.get("alerts", [])
            if not page_alerts:
                break
            fetched += len(page_alerts)
            for alert in page_alerts:
                if alert.get("is_shielded"):
                    continue
                strategy_name = (alert.get("strategy_name") or "").strip()
                if strategy_name not in alarm_name_set:
                    continue
                domain = self._extract_cluster_domain_from_alert_tags(alert.get("tags"))
                if not domain or domain in seen_domains:
                    continue
                seen_domains.add(domain)
                ordered_domains.append(domain)
                if len(ordered_domains) >= limit:
                    break
            total = int(data.get("total", 0))
            if fetched >= total or len(ordered_domains) >= limit:
                break
            query_param["page"] += 1
            if query_param["page"] > PRIORITY_ALARM_MAX_PAGES:
                break

        return ordered_domains

    def _base_cluster_qs(self, now: datetime):
        """Eligibility base queryset + lookback cutoff, shared by both lanes.

        Applies: cluster type / min-age / ONLINE phase, minus recently-checked and
        recently-NORMAL clusters, minus ignore-list. Does NOT drop busy clusters
        (that needs the paged ``ClusterOperateRecord`` join) and does NOT order.
        """
        lookback_cutoff = now - timedelta(days=self.config.lookback_days)
        cluster_types = self.config.cluster_types or ClusterType.redis_cluster_types()

        recently_checked_ids = self._build_recently_checked_ids(now)
        normal_skip_days = self.config.normal_skip_days or (self.config.lookback_days / 2)
        recently_normal_ids = set(
            RedisCheckReport.objects.filter(
                subtype=self.subtype.value,
                state=ReportStateType.NORMAL.value,
                create_at__gte=now - timedelta(days=normal_skip_days),
            ).values_list("cluster_id", flat=True)
        )

        skip_ids = recently_checked_ids | recently_normal_ids
        cluster_qs = Cluster.objects.filter(
            cluster_type__in=cluster_types,
            create_at__lte=lookback_cutoff,
            phase=ClusterPhase.ONLINE.value,
        ).exclude(id__in=skip_ids)
        if self.config.ignore_cluster_domains:
            cluster_qs = cluster_qs.exclude(immute_domain__in=self.config.ignore_cluster_domains)
        return cluster_qs, lookback_cutoff

    @staticmethod
    def _busy_cluster_ids(cluster_ids: list[int], lookback_cutoff: datetime) -> set[int]:
        """Return clusters with a recent or running exclusive ticket."""
        if not cluster_ids:
            return set()
        return set(
            ClusterOperateRecord.objects.filter(
                cluster_id__in=cluster_ids,
                ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
            )
            .filter(Q(ticket__create_at__gte=lookback_cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
            .values_list("cluster_id", flat=True)
        )

    @staticmethod
    def _to_items(cluster_ids: list[int]) -> list[RedisClusterItem]:
        """Attach immute_domain to each cluster_id, preserving order."""
        if not cluster_ids:
            return []
        domain_by_id = dict(Cluster.objects.filter(id__in=cluster_ids).values_list("id", "immute_domain"))
        missing = len(cluster_ids) - len(domain_by_id)
        if missing:
            logger.warning("redis agent selector: dropped %d clusters missing during item materialization", missing)
        return [{"cluster_id": cid, "cluster_domain": domain_by_id[cid]} for cid in cluster_ids if cid in domain_by_id]

    def select_priority(self, *, limit: int) -> list[RedisClusterItem]:
        """Return up to ``limit`` eligible alarm-driven clusters."""
        if limit <= 0:
            return []
        now = timezone.now()
        priority_domains = self._pull_priority_alarm_cluster_domains(now, limit=limit)
        if not priority_domains:
            return []
        base_qs, lookback_cutoff = self._base_cluster_qs(now)
        domain_to_id = dict(base_qs.filter(immute_domain__in=priority_domains).values_list("immute_domain", "id"))
        ordered_ids = [domain_to_id[d] for d in priority_domains if d in domain_to_id]
        busy_ids = self._busy_cluster_ids(ordered_ids, lookback_cutoff)
        alive_ids = [cluster_id for cluster_id in ordered_ids if cluster_id not in busy_ids]
        items = self._to_items(alive_ids)
        logger.info("%s: select_priority count=%d domains=%d", self.task_key, len(items), len(priority_domains))
        return items

    def select_rotation(self, *, cursor: int, limit: int) -> tuple[list[RedisClusterItem], int]:
        """Rotation lane: scan forward from ``cursor`` by id, return up to ``limit``.

        Returns ``(items, next_cursor)``. Scans ``candidate_page_size`` pages via
        ``id > cursor`` + LIMIT (index-friendly, bounded per run). When the id
        space is exhausted, ``next_cursor`` wraps to 0 so the next run restarts
        from the head — coverage is eventually-complete across runs/days even if
        a single day cannot finish the full set.
        """
        if limit <= 0:
            return [], cursor
        now = timezone.now()
        base_qs, lookback_cutoff = self._base_cluster_qs(now)
        page_size = max(1, self.config.candidate_page_size)
        derived_scan_limit = max(limit, page_size) * 5
        configured_scan_limit = max(0, int(self.config.max_candidate_scan))
        max_scan = min(derived_scan_limit, configured_scan_limit) if configured_scan_limit else derived_scan_limit

        collected: list[int] = []
        last_seen = max(0, int(cursor))
        next_cursor = last_seen
        scanned = 0
        while len(collected) < limit and scanned < max_scan:
            fetch_size = min(page_size, max_scan - scanned)
            page_ids = list(base_qs.filter(id__gt=last_seen).order_by("id").values_list("id", flat=True)[:fetch_size])
            if not page_ids:
                next_cursor = 0  # exhausted id space; wrap for the next run
                break
            busy_ids = self._busy_cluster_ids(page_ids, lookback_cutoff)
            for cid in page_ids:
                scanned += 1
                last_seen = cid
                next_cursor = cid
                if cid not in busy_ids:
                    collected.append(cid)
                if len(collected) >= limit:
                    break

        items = self._to_items(collected[:limit])
        logger.info(
            "%s: select_rotation cursor=%d->%d count=%d scanned=%d",
            self.task_key,
            cursor,
            next_cursor,
            len(items),
            scanned,
        )
        return items, next_cursor
