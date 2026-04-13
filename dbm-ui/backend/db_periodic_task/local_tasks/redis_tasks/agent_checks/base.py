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
import dataclasses
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import timedelta
from typing import Callable, ClassVar

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.utils import calculate_countdown
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models import RedisCheckReport
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models import ClusterOperateRecord

logger = logging.getLogger("root")

# Redis ticket types that block agent checks due to active cluster instability.
# Intentionally excludes REDIS_SCALE_UPDOWN, REDIS_CLUSTER_AUTOFIX,
# REDIS_CLUSTER_INS_MIGRATE and REDIS_SINGLE_INS_MIGRATE: these operations
# complete quickly enough that they do not invalidate metric-based analysis,
# and excluding them avoids unnecessarily delaying checks on busy clusters.
REDIS_EXCLUSIVE_TICKET_TYPES = [
    TicketType.REDIS_DTS_ONLINE_SWITCH.value,
    TicketType.REDIS_MASTER_SLAVE_SWITCH.value,
    TicketType.REDIS_CLUSTER_CUTOFF.value,
    TicketType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
    TicketType.REDIS_CLUSTER_TYPE_UPDATE.value,
    TicketType.REDIS_CLUSTER_REINSTALL_DBMON.value,
]

TICKET_RUNNING_STATUS_VALUES = [s.value for s in TICKET_RUNNING_STATUS_SET]

DEFAULT_LOOKBACK_DAYS = 7

DISPATCH_INTERVAL_SECONDS = 10 * 60  # must match crontab(minute="*/10") in task.py
DISPATCH_EXPIRE_BUFFER_SECONDS = 60
DISPATCH_SPREAD_SECONDS = DISPATCH_INTERVAL_SECONDS - DISPATCH_EXPIRE_BUFFER_SECONDS
DISPATCH_RATE_LIMIT_COOLDOWN_SECONDS = 60
DEFAULT_MAX_RATE_LIMIT_RETRIES = 3
PRIORITY_ALARM_DAILY_DOMAIN_CACHE_KEY_PREFIX = "redis_agent_check_priority_alarm_domains"
PRIORITY_ALARM_DAILY_DOMAIN_CACHE_LOCK_KEY_PREFIX = "redis_agent_check_priority_alarm_domains_lock"
PRIORITY_ALARM_DAILY_CONSUME_LOCK_TTL_SECONDS = 15
PRIORITY_ALARM_MAX_PAGES = 50  # 50 * 200 = 10,000 alerts

_RATE_LIMIT_PATTERN = re.compile(r"429|rate.?limit", re.IGNORECASE)


def _is_rate_limit_error(exc: Exception) -> bool:
    return bool(_RATE_LIMIT_PATTERN.search(str(exc)))


def _should_skip(config: "BaseCheckConfig", cluster: Cluster) -> tuple[bool, str]:
    """Skip clusters that are young, offline, in ignore list, or have recent/active tickets."""
    now = timezone.now()

    if cluster.create_at > now - timedelta(days=config.lookback_days):
        return True, f"skipped: cluster younger than {config.lookback_days} days"

    if cluster.phase != ClusterPhase.ONLINE.value:
        return True, f"skipped: cluster phase={cluster.phase} is not online"

    if cluster.immute_domain in config.ignore_cluster_domains:
        return True, "skipped: cluster in ignore list"

    cutoff = now - timedelta(days=config.lookback_days)
    has_recent = (
        ClusterOperateRecord.objects.filter(
            cluster_id=cluster.id,
            ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
        )
        .filter(Q(ticket__create_at__gte=cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
        .exists()
    )
    if has_recent:
        return True, "skipped: recent or active capacity/autofix/migrate ticket"

    return False, ""


def execute_agent_check(
    agent_code: DBMAgentCode,
    prompt_template: str,
    config: "BaseCheckConfig",
    cluster_id: int,
    celery_task=None,
):
    """Run an agent check for a single cluster with rate-limit backoff.

    If *celery_task* is a bound Celery task instance, 429 errors trigger
    ``celery_task.retry(countdown=rate_limit_cooldown_seconds)`` instead of
    failing immediately.  The retried task may expire before execution,
    which is acceptable.
    """
    task_label = celery_task.name if celery_task else str(agent_code)

    try:
        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            logger.warning("%s: cluster_id=%s not found", task_label, cluster_id)
            return

        skipped, reason = _should_skip(config, cluster)
        if skipped:
            logger.debug("%s: cluster_id=%s %s", task_label, cluster_id, reason)
            return

        from backend.dbm_aiagent.agent.handlers import AgentHandler

        content = prompt_template.format(cluster_domain=cluster.immute_domain)
        AgentHandler.ask_agent_with_content(
            agent_code=agent_code,
            content=content,
        )
        logger.info("%s: cluster_id=%s done", task_label, cluster_id)

    except Exception as e:
        if _is_rate_limit_error(e) and celery_task is not None:
            cooldown = max(1, config.rate_limit_cooldown_seconds)
            max_retries = max(0, config.max_rate_limit_retries)
            if celery_task.request.retries < max_retries:
                logger.warning(
                    "%s: cluster_id=%s hit rate limit (attempt %d/%d), retrying in %ds: %s",
                    task_label,
                    cluster_id,
                    celery_task.request.retries + 1,
                    max_retries,
                    cooldown,
                    e,
                )
                raise celery_task.retry(
                    countdown=cooldown, max_retries=max_retries, exc=e, expires=DISPATCH_INTERVAL_SECONDS
                )

        logger.exception("%s: cluster_id=%s failed: %s", task_label, cluster_id, e)


@dataclass
class BaseCheckConfig:
    setting_key: ClassVar[str] = ""
    enabled: bool = False
    batch_size: int = 40
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ignore_cluster_domains: list = field(default_factory=list)
    cluster_types: list = field(default_factory=list)
    candidate_scan_multiplier: int = 2
    candidate_page_size: int = 200
    max_candidate_scan: int = 0
    selection_strategy: str = "sequential"  # sequential | rotating
    # Keep rolling 24h behavior by default; calendar_day can be enabled later via config.
    recent_check_mode: str = "rolling_24h"  # rolling_24h | calendar_day
    # 0 means use fallback (lookback_days / 2) to preserve current behavior.
    normal_skip_days: float = 0
    enable_inflight_dedupe: bool = False
    # Keep lock TTL aligned with one dispatch interval so stale locks self-expire before next cycle.
    inflight_lock_ttl_seconds: int = DISPATCH_INTERVAL_SECONDS
    rate_limit_cooldown_seconds: int = DISPATCH_RATE_LIMIT_COOLDOWN_SECONDS
    max_rate_limit_retries: int = DEFAULT_MAX_RATE_LIMIT_RETRIES
    # Names are matched against the alert's strategy_name (the clean policy name),
    # not alert_name (which carries dynamic business-name suffixes at runtime).
    priority_alarm_names: list = field(default_factory=list)
    # API time-window width; should be wide enough to capture all active alerts.
    priority_alarm_lookback_hours: int = 24 * 30
    # Optional coarse request-side alert_name narrowing in query_string.
    # Kept off by default because client-side matching uses strategy_name, and
    # the API query_string does not support strategy_name filtering.
    priority_alarm_request_name_filter: bool = False

    @classmethod
    def from_raw(cls, raw: dict):
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in valid_keys})

    @classmethod
    def from_settings(cls):
        from backend.configuration.models import SystemSettings

        if not cls.setting_key:
            raise ValueError(f"{cls.__name__} must declare a non-empty setting_key")
        raw = SystemSettings.get_setting_value(cls.setting_key, default={})
        if not isinstance(raw, dict):
            return cls()
        return cls.from_raw(raw)

    def save_to_settings(self):
        from backend.configuration.models import SystemSettings

        SystemSettings.insert_setting_value(self.setting_key, dataclasses.asdict(self))


class BaseRedisAgentCheckTask(ABC):
    """Base class for Redis periodic LLM agent check dispatchers.

    Handles candidate selection, dedup, and Celery dispatch.  Worker-side
    execution logic lives in the standalone ``execute_agent_check()`` function.

    To add a new check type:
      1. Create a thin subclass declaring `subtype`, `agent_code`, `prompt_template`, and `load_config()`.
      2. Define a bound Celery task that calls ``execute_agent_check()`` with explicit params.
      3. Register a periodic task in task.py.
    """

    # Subclasses must declare these:
    subtype: RedisCheckSubType
    agent_code: DBMAgentCode
    prompt_template: str  # plain Python format string, e.g. "cluster_domains: [{cluster_domain}]"

    def __init__(self):
        self.config = self.load_config()

    @abstractmethod
    def load_config(self) -> BaseCheckConfig:
        """Return the config for this check type. Called once during __init__."""

    @abstractmethod
    def get_celery_task(self) -> Callable:
        """Return the bound Celery task function used to dispatch per-cluster work."""

    def _resolve_selection_strategy(self) -> str:
        strategy = (self.config.selection_strategy or "sequential").lower()
        if strategy not in {"sequential", "rotating"}:
            logger.warning(
                "%s: invalid selection_strategy=%s, fallback to sequential",
                type(self).__name__,
                self.config.selection_strategy,
            )
            return "sequential"
        return strategy

    def _resolve_max_candidate_scan(self) -> int:
        if self.config.max_candidate_scan and self.config.max_candidate_scan > 0:
            return self.config.max_candidate_scan

        batch_size = max(1, self.config.batch_size)
        multiplier = max(1, self.config.candidate_scan_multiplier)
        return batch_size * multiplier

    def _build_recently_checked_ids(self, now) -> set:
        # Maintain current behavior by default (rolling 24h), but allow explicit calendar-day mode.
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

    def _get_rotation_pivot(self, now, candidate_count: int) -> int:
        # Time-bucketed deterministic rotation. We rotate within the scanned window, not full table cardinality.
        if candidate_count <= 0:
            return 0
        bucket = int(now.timestamp() // DISPATCH_INTERVAL_SECONDS)
        return max(0, bucket % candidate_count)

    def _build_inflight_dedupe_key(self, cluster_id: int) -> str:
        return f"redis_agent_check_dispatch_lock:{self.subtype.value}:{cluster_id}"

    def _build_priority_alarm_daily_domain_cache_key(self) -> str:
        return f"{PRIORITY_ALARM_DAILY_DOMAIN_CACHE_KEY_PREFIX}:{self.subtype.value}"

    def _build_priority_alarm_daily_domain_cache_lock_key(self) -> str:
        return f"{PRIORITY_ALARM_DAILY_DOMAIN_CACHE_LOCK_KEY_PREFIX}:{self.subtype.value}"

    @staticmethod
    def _cache_release_lock(lock_key: str, owner: str):
        """Release a cache lock only if it is still owned by *owner*.

        Prevents a slow holder whose TTL has already expired from deleting
        a lock that was since re-acquired by another worker.
        """

        if cache.get(lock_key) == owner:
            cache.delete(lock_key)

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
        base_query = 'labels: "DBM_REDIS"'
        if not self.config.priority_alarm_request_name_filter:
            return base_query
        if not alarm_name_set:
            return base_query

        name_filter = " OR ".join(f'alert_name: "{name}"' for name in sorted(alarm_name_set))
        return f"{base_query} AND ({name_filter})"

    def _pull_priority_alarm_cluster_domains(self, now) -> list:
        alarm_name_set = {
            name.strip() for name in self.config.priority_alarm_names if isinstance(name, str) and name.strip()
        }
        if not alarm_name_set:
            return []

        lookback_hours = max(1, int(self.config.priority_alarm_lookback_hours))
        start_time = now - timedelta(hours=lookback_hours)
        query_param = {
            "bk_biz_ids": [],
            "start_time": int(start_time.timestamp()),
            "end_time": int(now.timestamp()),
            "page": 1,
            "page_size": 200,
            "status": ["ABNORMAL"],
            "show_aggs": False,
            "show_overview": False,
            "query_string": self._build_alarm_query_string(alarm_name_set),
        }

        query_param["bk_biz_ids"] = [env.DBA_APP_BK_BIZ_ID]

        alerts = []
        fetched = 0
        while True:
            data = BKMonitorV3Api.search_alert(query_param)
            page_alerts = data.get("alerts", [])
            if not page_alerts:
                break
            alerts.extend(page_alerts)
            fetched += len(page_alerts)
            total = int(data.get("total", 0))
            if fetched >= total:
                break
            query_param["page"] += 1
            if query_param["page"] > PRIORITY_ALARM_MAX_PAGES:
                logger.warning(
                    "%s: alarm pagination exceeded %d pages, truncating results (fetched=%d, total=%d)",
                    type(self).__name__,
                    PRIORITY_ALARM_MAX_PAGES,
                    fetched,
                    total,
                )
                break

        ordered_domains = []
        seen_domains = set()
        for alert in alerts:
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

        return ordered_domains

    def build_daily_alarm_priority_domain_cache(self, now=None) -> list:
        if not self.config.priority_alarm_names:
            return []

        now = now or timezone.now()
        alarm_name_set = sorted(
            {name.strip() for name in self.config.priority_alarm_names if isinstance(name, str) and name.strip()}
        )
        if not alarm_name_set:
            return []

        try:
            ordered_domains = self._pull_priority_alarm_cluster_domains(now=now)
        except Exception as err:
            logger.warning("%s: daily priority alarm query failed: %s", type(self).__name__, err)
            return []

        lock_key = self._build_priority_alarm_daily_domain_cache_lock_key()
        owner = uuid.uuid4().hex
        if not cache.add(lock_key, owner, timeout=PRIORITY_ALARM_DAILY_CONSUME_LOCK_TTL_SECONDS):
            logger.warning(
                "%s: daily priority domain cache build skipped due to lock contention",
                type(self).__name__,
            )
            return []

        try:
            cache.set(
                self._build_priority_alarm_daily_domain_cache_key(),
                {
                    "remaining_domains": ordered_domains,
                    "total_domains": len(ordered_domains),
                    "alarm_names": alarm_name_set,
                    "refreshed_at": int(now.timestamp()),
                },
                timeout=24 * 60 * 60,
            )
        finally:
            self._cache_release_lock(lock_key, owner)

        logger.info(
            "%s: built_daily_priority_domain_cache total_domains=%d alarm_names=%s",
            type(self).__name__,
            len(ordered_domains),
            alarm_name_set,
        )
        return ordered_domains

    def _consume_daily_priority_domains(self, now, consume_limit: int) -> list:
        if not self.config.priority_alarm_names:
            return []
        if consume_limit <= 0:
            return []

        cache_key = self._build_priority_alarm_daily_domain_cache_key()
        lock_key = self._build_priority_alarm_daily_domain_cache_lock_key()
        owner = uuid.uuid4().hex
        if not cache.add(lock_key, owner, timeout=PRIORITY_ALARM_DAILY_CONSUME_LOCK_TTL_SECONDS):
            logger.info("%s: daily priority domain cache lock contention, skip consume", type(self).__name__)
            return []

        try:
            payload = cache.get(cache_key)
            if not isinstance(payload, dict):
                return []

            remaining_domains = payload.get("remaining_domains")
            if not isinstance(remaining_domains, list) or not remaining_domains:
                return []

            picked_domains = remaining_domains[:consume_limit]
            payload["remaining_domains"] = remaining_domains[consume_limit:]
            payload["consumed_count"] = payload.get("total_domains", 0) - len(payload["remaining_domains"])
            cache.set(cache_key, payload, timeout=24 * 60 * 60)
            return picked_domains
        finally:
            self._cache_release_lock(lock_key, owner)

    def get_clusters_to_check(self) -> list:
        """Fetch a batch of Redis clusters for this subtype."""
        now = timezone.now()
        lookback_cutoff = now - timedelta(days=self.config.lookback_days)
        cluster_types = self.config.cluster_types or ClusterType.redis_cluster_types()

        # recently_checked_ids uses a Python set instead of a subquery because
        # RedisCheckReport and Cluster are on different databases.
        recently_checked_ids = self._build_recently_checked_ids(now)

        # Normal clusters are suppressed for a longer window (normal_skip_days,
        # default lookback_days/2) so healthy clusters aren't re-checked too soon,
        # while abnormal/unknown clusters only use the shorter recently_checked_ids
        # window (rolling 24h or calendar-day) and re-enter the candidate pool sooner.
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

        batch_size = max(1, self.config.batch_size)
        max_scan = self._resolve_max_candidate_scan()
        page_size = max(1, self.config.candidate_page_size)
        strategy = self._resolve_selection_strategy()

        consumed_domains = self._consume_daily_priority_domains(now=now, consume_limit=batch_size)
        dropped_domains = []
        priority_ids = []
        if consumed_domains:
            domain_to_id = dict(
                cluster_qs.filter(immute_domain__in=consumed_domains).values_list("immute_domain", "id")
            )
            priority_ids = [domain_to_id[domain] for domain in consumed_domains if domain in domain_to_id]
            dropped_domains = [domain for domain in consumed_domains if domain not in domain_to_id]
            if dropped_domains:
                logger.warning(
                    "%s: dropped priority domains not eligible in current candidate set " "(count=%d, sample=%s)",
                    type(self).__name__,
                    len(dropped_domains),
                    dropped_domains[:5],
                )

        base_candidate_ids = list(cluster_qs.order_by("id").values_list("id", flat=True)[:max_scan])
        if not base_candidate_ids and not priority_ids:
            return []

        if strategy == "rotating" and len(base_candidate_ids) > 1:
            pivot = self._get_rotation_pivot(now, len(base_candidate_ids))
            candidate_ids = base_candidate_ids[pivot:] + base_candidate_ids[:pivot]
        else:
            candidate_ids = base_candidate_ids

        if priority_ids:
            priority_id_set = set(priority_ids)
            candidate_ids = priority_ids + [
                cluster_id for cluster_id in candidate_ids if cluster_id not in priority_id_set
            ]

        result = []
        scanned = 0
        busy_hits = 0
        early_stop_reason = "exhausted_candidates"

        for idx in range(0, len(candidate_ids), page_size):
            if len(result) >= batch_size:
                early_stop_reason = "batch_filled"
                break

            page_ids = candidate_ids[idx : idx + page_size]
            scanned += len(page_ids)
            page_busy_ids = set(
                ClusterOperateRecord.objects.filter(
                    cluster_id__in=page_ids,
                    ticket__ticket_type__in=REDIS_EXCLUSIVE_TICKET_TYPES,
                )
                .filter(Q(ticket__create_at__gte=lookback_cutoff) | Q(ticket__status__in=TICKET_RUNNING_STATUS_VALUES))
                .values_list("cluster_id", flat=True)
            )
            busy_hits += len(page_busy_ids)

            for cluster_id in page_ids:
                if cluster_id in page_busy_ids:
                    continue
                result.append(cluster_id)
                if len(result) >= batch_size:
                    early_stop_reason = "batch_filled"
                    break

        logger.info(
            "%s: selected=%d requested=%d scanned=%d busy_hits=%d "
            "priority_hits=%d priority_consumed=%d "
            "priority_dropped=%d priority_dropped_domains=%s strategy=%s stop=%s",
            type(self).__name__,
            len(result),
            batch_size,
            scanned,
            busy_hits,
            len(priority_ids),
            len(consumed_domains),
            len(dropped_domains),
            dropped_domains,
            strategy,
            early_stop_reason,
        )
        return result

    def start(self) -> int:
        """Dispatch a batch of clusters for LLM analysis. Returns the number dispatched."""
        task_name = type(self).__name__

        if not self.config.enabled:
            logger.info("%s: disabled by config", task_name)
            return 0

        cluster_ids = self.get_clusters_to_check()
        if not cluster_ids:
            logger.debug("%s: no clusters to check", task_name)
            return 0

        celery_task = self.get_celery_task()
        config_dict = dataclasses.asdict(self.config)
        dispatched = 0
        dedupe_skipped = 0
        count = len(cluster_ids)
        for idx, cluster_id in enumerate(cluster_ids):
            lock_key = ""
            try:
                if self.config.enable_inflight_dedupe:
                    lock_key = self._build_inflight_dedupe_key(cluster_id)
                    lock_ttl = max(1, int(self.config.inflight_lock_ttl_seconds))
                    if not cache.add(lock_key, 1, timeout=lock_ttl):
                        dedupe_skipped += 1
                        continue

                countdown = calculate_countdown(count=count, index=idx, duration=DISPATCH_SPREAD_SECONDS)
                celery_task.apply_async(
                    args=[cluster_id, config_dict], countdown=countdown, expires=DISPATCH_INTERVAL_SECONDS
                )
                dispatched += 1
            except Exception as e:
                if lock_key:
                    cache.delete(lock_key)
                logger.error("%s: failed to dispatch cluster_id=%s: %s", task_name, cluster_id, e)

        logger.info(
            "%s: dispatched %d/%d clusters (dedupe_skipped=%d, sample ids=%s)",
            task_name,
            dispatched,
            count,
            dedupe_skipped,
            cluster_ids[:5] if len(cluster_ids) >= 5 else cluster_ids,
        )
        return dispatched
