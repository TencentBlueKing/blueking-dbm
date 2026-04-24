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
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import timedelta
from typing import Callable, ClassVar

from celery.exceptions import SoftTimeLimitExceeded
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

# Layered timeouts for a single agent check. Two invariants must hold:
#   1. invoke_timeout < soft_time_limit < hard_time_limit
#      SDK-level timeout aborts gracefully first, Celery's soft limit is the
#      Python-level fallback, and the hard limit is the last-resort SIGKILL
#      against native hangs.
#   2. hard_time_limit <= DISPATCH_INTERVAL_SECONDS
#      A cycle-N task must not occupy a worker slot past the start of
#      cycle-(N+1). Otherwise slow stragglers silently reduce the capacity
#      available to the next batch, because apply_async(expires=...) then
#      drops fresh tasks in favor of finishing old ones.
DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS = 540
DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS = 570
DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS = 600

# Cap how many characters of an agent response we log. A single report is
# typically ~400-600 chars; this leaves generous headroom for multi-table
# outputs while preventing a runaway response from flooding the log pipeline.
AGENT_RESPONSE_LOG_MAX_CHARS = 2000

# Structured outcome tags for log aggregation. Every terminal log line
# emitted by execute_agent_check, the task_failure handler in signals.py,
# or start()'s dispatch loop carries `outcome=<one of the below>` so
# external log platforms (ES/Datadog) can cleanly count per-cycle
# distributions. When adding new outcomes, keep them snake_case and
# document them here.
OUTCOME_SUCCESS = "success"  # agent call returned normally
OUTCOME_TIMEOUT_INVOKE = "timeout_invoke"  # SDK-level invoke_timeout fired (graceful first layer)
OUTCOME_TIMEOUT_SOFT = "timeout_soft"  # Celery SoftTimeLimitExceeded fired
OUTCOME_TIMEOUT_HARD = "timeout_hard"  # worker SIGKILLed at time_limit (WorkerLostError)
OUTCOME_RATELIMIT_RETRY = "ratelimit_retry"  # 429 detected, celery retry scheduled
OUTCOME_RATELIMIT_GAVE_UP = "ratelimit_gave_up"  # 429 but max retries reached
OUTCOME_ERROR = "error"  # any other uncaught exception from the agent call
OUTCOME_SKIPPED = "skipped"  # cluster skipped pre-agent; specific cause in the reason field
# Dispatch-side outcomes: emitted by start(), not by the worker.
OUTCOME_DISPATCH_OK = "dispatch_ok"
OUTCOME_DISPATCH_FAILED = "dispatch_failed"
OUTCOME_DISPATCH_DEDUP_SKIPPED = "dispatch_dedup_skipped"

PRIORITY_ALARM_DAILY_DOMAIN_CACHE_KEY_PREFIX = "redis_agent_check_priority_alarm_domains"
PRIORITY_ALARM_DAILY_DOMAIN_CACHE_LOCK_KEY_PREFIX = "redis_agent_check_priority_alarm_domains_lock"
PRIORITY_ALARM_DAILY_CONSUME_LOCK_TTL_SECONDS = 15
PRIORITY_ALARM_MAX_PAGES = 50  # 50 * 200 = 10,000 alerts

_RATE_LIMIT_PATTERN = re.compile(r"429|rate.?limit", re.IGNORECASE)


def _is_rate_limit_error(exc: Exception) -> bool:
    return bool(_RATE_LIMIT_PATTERN.search(str(exc)))


def _truncate_agent_response_for_log(response, max_chars: int = AGENT_RESPONSE_LOG_MAX_CHARS) -> str:
    """Coerce an agent response to a bounded single-line repr for logging.

    Non-string responses (None, dict, etc.) are passed through repr() unchanged
    so unexpected upstream shapes stay debuggable. Long strings are truncated
    with a trailing marker showing the original length.
    """
    if not isinstance(response, str):
        return repr(response)
    if len(response) <= max_chars:
        return repr(response)
    return f"{response[:max_chars]!r}...[truncated, total_len={len(response)}]"


def _should_skip(config: "BaseCheckConfig", cluster: Cluster) -> tuple[bool, str]:
    """Decide whether to skip this cluster.

    Returns (skipped, human_reason). The outcome tag for all skip paths is
    uniformly ``OUTCOME_SKIPPED``; the specific cause (young / offline /
    ignored / busy) is carried in ``human_reason`` and emitted as a
    ``reason=...`` field alongside ``outcome=skipped`` in logs.
    """
    now = timezone.now()

    if cluster.create_at > now - timedelta(days=config.lookback_days):
        return True, f"cluster younger than {config.lookback_days} days"

    if cluster.phase != ClusterPhase.ONLINE.value:
        return True, f"cluster phase={cluster.phase} is not online"

    if cluster.immute_domain in config.ignore_cluster_domains:
        return True, "cluster in ignore list"

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
        return True, "recent or active capacity/autofix/migrate ticket"

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

    Failure semantics (intentional):
      - ``OUTCOME_RATELIMIT_GAVE_UP`` (retries exhausted) is a **soft
        failure** -- we log at ERROR and return normally without
        re-raising.  The Celery task is therefore marked SUCCESS.
        Downstream monitoring must tail the outcome tag in logs rather
        than rely on Celery task failure state to detect this case.
      - ``OUTCOME_TIMEOUT_SOFT`` (SoftTimeLimitExceeded) is also soft-
        swallowed for the same reason: continued retries under rate
        pressure rarely help and only amplify load.
      - ``OUTCOME_TIMEOUT_INVOKE`` (SDK-level invoke_timeout fired via
        ``asyncio.wait_for`` inside ``aidev_agent``) is the graceful
        first layer of the timeout cascade and is also soft-swallowed.
        Logged at WARNING without a traceback since the async stack is
        always identical and non-diagnostic.
      - All other exceptions fall through to the generic ``logger.exception``
        at the bottom, which similarly does not re-raise.  Celery retries
        are only triggered explicitly via ``celery_task.retry`` in the
        rate-limit path above.
    """
    task_label = celery_task.name if celery_task else str(agent_code)

    try:
        cluster = Cluster.objects.filter(id=cluster_id).first()
        if not cluster:
            logger.warning(
                "%s: cluster_id=%s outcome=%s reason=%s",
                task_label,
                cluster_id,
                OUTCOME_SKIPPED,
                "cluster not found",
            )
            return

        skipped, skip_reason = _should_skip(config, cluster)
        if skipped:
            logger.debug(
                "%s: cluster_id=%s outcome=%s reason=%s",
                task_label,
                cluster_id,
                OUTCOME_SKIPPED,
                skip_reason,
            )
            return

        from backend.dbm_aiagent.agent.handlers import AgentHandler

        content = prompt_template.format(cluster_domain=cluster.immute_domain)
        invoke_timeout = max(1, int(config.agent_invoke_timeout_seconds))
        invoke_started_at = time.monotonic()
        try:
            ai_response = AgentHandler.ask_agent_with_content(
                agent_code=agent_code,
                content=content,
                timeout=invoke_timeout,
            )
        except BaseException:
            # Annotate the elapsed invoke duration so downstream handlers can
            # tell SDK-level timeouts apart from Celery soft-limit / upstream cancels.
            _invoke_elapsed = time.monotonic() - invoke_started_at
            raise
        invoke_elapsed = time.monotonic() - invoke_started_at
        logger.info(
            "%s: cluster_id=%s outcome=%s elapsed=%.2fs invoke_timeout=%ds agent_response=%s",
            task_label,
            cluster_id,
            OUTCOME_SUCCESS,
            invoke_elapsed,
            invoke_timeout,
            _truncate_agent_response_for_log(ai_response),
        )

    except SoftTimeLimitExceeded as e:
        # Celery soft-limit fired: SDK-level invoke_timeout did not abort in time.
        # Log loudly and return — do NOT retry, as continued rate pressure is unlikely
        # to help and may mask a broken upstream.
        logger.error(
            "%s: cluster_id=%s outcome=%s elapsed=%.2fs soft_time_limit=%ds invoke_timeout=%ds: %s",
            task_label,
            cluster_id,
            OUTCOME_TIMEOUT_SOFT,
            locals().get("_invoke_elapsed", -1.0),
            config.agent_soft_time_limit_seconds,
            config.agent_invoke_timeout_seconds,
            e,
        )
    except TimeoutError as e:
        # SDK-level invoke_timeout (aidev_agent run_coro_sync / asyncio.wait_for) fired.
        # This is the FIRST, graceful layer of the timeout cascade (see module-level
        # comment on layered timeouts). Log at WARNING without a traceback; the async
        # stack is always identical and carries no diagnostic value.
        logger.warning(
            "%s: cluster_id=%s outcome=%s elapsed=%.2fs invoke_timeout=%ds: %s",
            task_label,
            cluster_id,
            OUTCOME_TIMEOUT_INVOKE,
            locals().get("_invoke_elapsed", -1.0),
            config.agent_invoke_timeout_seconds,
            e,
        )
    except Exception as e:
        if _is_rate_limit_error(e) and celery_task is not None:
            cooldown = max(1, config.rate_limit_cooldown_seconds)
            max_retries = max(0, config.max_rate_limit_retries)
            if celery_task.request.retries < max_retries:
                logger.warning(
                    "%s: cluster_id=%s outcome=%s attempt=%d/%d cooldown=%ds: %s",
                    task_label,
                    cluster_id,
                    OUTCOME_RATELIMIT_RETRY,
                    celery_task.request.retries + 1,
                    max_retries,
                    cooldown,
                    e,
                )
                raise celery_task.retry(
                    countdown=cooldown, max_retries=max_retries, exc=e, expires=DISPATCH_INTERVAL_SECONDS
                )
            # Rate limit retries exhausted: tag separately so the generic
            # ERROR bucket stays informative, and skip the logger.exception
            # below to avoid a second log line for the same root cause.
            logger.error(
                "%s: cluster_id=%s outcome=%s attempts=%d: %s",
                task_label,
                cluster_id,
                OUTCOME_RATELIMIT_GAVE_UP,
                celery_task.request.retries,
                e,
            )
            return

        logger.exception(
            "%s: cluster_id=%s outcome=%s elapsed=%.2fs invoke_timeout=%ds: %s",
            task_label,
            cluster_id,
            OUTCOME_ERROR,
            locals().get("_invoke_elapsed", -1.0),
            config.agent_invoke_timeout_seconds,
            e,
        )


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
    selection_strategy: str = "rotating"  # sequential | rotating
    # Keep rolling 24h behavior by default; calendar_day can be enabled later via config.
    recent_check_mode: str = "rolling_24h"  # rolling_24h | calendar_day
    # 0 means use fallback (lookback_days / 2) to preserve current behavior.
    normal_skip_days: float = 0
    enable_inflight_dedupe: bool = False
    # Keep lock TTL aligned with one dispatch interval so stale locks self-expire before next cycle.
    inflight_lock_ttl_seconds: int = DISPATCH_INTERVAL_SECONDS
    rate_limit_cooldown_seconds: int = DISPATCH_RATE_LIMIT_COOLDOWN_SECONDS
    max_rate_limit_retries: int = DEFAULT_MAX_RATE_LIMIT_RETRIES
    # Layered per-cluster timeouts. See DEFAULT_AGENT_* constants above for the
    # invariant (invoke < soft < hard) and the reasoning behind each layer.
    agent_invoke_timeout_seconds: int = DEFAULT_AGENT_INVOKE_TIMEOUT_SECONDS
    agent_soft_time_limit_seconds: int = DEFAULT_AGENT_SOFT_TIME_LIMIT_SECONDS
    agent_hard_time_limit_seconds: int = DEFAULT_AGENT_HARD_TIME_LIMIT_SECONDS
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
      4. Optionally override ``extra_skip_check()`` to express check-specific
         dispatch-time skip rules (e.g. dbconfig-driven policy checks).
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

    def extra_skip_check(self, cluster: Cluster) -> tuple[bool, str]:
        """Subclass-specific dispatch-time skip rule. Default: never skip.

        Override on a subclass to express skip rules that the generic
        ``_should_skip`` cannot capture (e.g. configuration-driven skips
        that need a dbconfig lookup, like Redis ``maxmemory-policy``).

        The hook runs inside ``get_clusters_to_check`` after the busy-
        ticket filter and *before* Celery dispatch, so a skip here frees
        the worker slot for another candidate instead of paying the
        round-trip cost of a noop task.

        Must fail open: ``get_clusters_to_check`` catches any exception
        raised here and treats the cluster as eligible. Otherwise a
        misbehaving rule could silently suppress an entire check across
        the fleet.
        """
        return False, ""

    def _has_extra_skip_check(self) -> bool:
        """True iff a subclass actually overrides ``extra_skip_check``.

        Used by ``get_clusters_to_check`` to skip the per-page Cluster
        fetch when no subclass cares, keeping the default-path query
        cost identical to before this hook existed.
        """
        return type(self).extra_skip_check is not BaseRedisAgentCheckTask.extra_skip_check

    def _resolve_agent_timeouts(self) -> tuple[int, int, int]:
        """Return (invoke_timeout, soft_time_limit, hard_time_limit) from config.

        Config is authoritative — values flow through unchanged so operators
        can override at runtime via SystemSettings without us silently
        rewriting their intent. Two invariants are checked and any violation
        is logged as a warning so ops can spot misconfiguration:

          1. invoke_timeout < soft_time_limit < hard_time_limit
             (defense-in-depth layering; see DEFAULT_AGENT_* constants)
          2. hard_time_limit <= DISPATCH_INTERVAL_SECONDS
             (tasks should finish before the next dispatch cycle; exceeding
             this lets slow stragglers occupy worker slots across cycles)

        Only non-positive values are defensively coerced to 1 so apply_async
        does not reject the dispatch entirely.
        """
        invoke = max(1, int(self.config.agent_invoke_timeout_seconds))
        soft = max(1, int(self.config.agent_soft_time_limit_seconds))
        hard = max(1, int(self.config.agent_hard_time_limit_seconds))

        issues = []
        if not (invoke < soft < hard):
            issues.append(f"invoke<soft<hard violated (invoke={invoke}, soft={soft}, hard={hard})")
        if hard > DISPATCH_INTERVAL_SECONDS:
            issues.append(
                f"hard_time_limit={hard}s exceeds "
                f"DISPATCH_INTERVAL_SECONDS={DISPATCH_INTERVAL_SECONDS}s; "
                "slow tasks may occupy worker slots across dispatch cycles"
            )
        if issues:
            logger.warning(
                "%s: agent timeout config issues: %s",
                type(self).__name__,
                "; ".join(issues),
            )

        return invoke, soft, hard

    def _resolve_selection_strategy(self) -> str:
        strategy = (self.config.selection_strategy or "rotating").lower()
        if strategy not in {"sequential", "rotating"}:
            logger.warning(
                "%s: invalid selection_strategy=%s, fallback to rotating",
                type(self).__name__,
                self.config.selection_strategy,
            )
            return "rotating"
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
        extra_skip_hits = 0
        task_name = type(self).__name__
        has_extra_skip = self._has_extra_skip_check()
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

            page_extra_skipped_ids = self._apply_extra_skip_check(
                task_name=task_name,
                page_ids=page_ids,
                page_busy_ids=page_busy_ids,
                has_extra_skip=has_extra_skip,
            )
            extra_skip_hits += len(page_extra_skipped_ids)

            for cluster_id in page_ids:
                if cluster_id in page_busy_ids:
                    continue
                if cluster_id in page_extra_skipped_ids:
                    continue
                result.append(cluster_id)
                if len(result) >= batch_size:
                    early_stop_reason = "batch_filled"
                    break

        logger.info(
            "%s: selected=%d requested=%d scanned=%d busy_hits=%d extra_skip_hits=%d "
            "priority_hits=%d priority_consumed=%d "
            "priority_dropped=%d priority_dropped_domains=%s strategy=%s stop=%s",
            task_name,
            len(result),
            batch_size,
            scanned,
            busy_hits,
            extra_skip_hits,
            len(priority_ids),
            len(consumed_domains),
            len(dropped_domains),
            dropped_domains,
            strategy,
            early_stop_reason,
        )
        return result

    def _apply_extra_skip_check(
        self,
        *,
        task_name: str,
        page_ids: list,
        page_busy_ids: set,
        has_extra_skip: bool,
    ) -> set:
        """Run the subclass ``extra_skip_check`` on the non-busy IDs of a page.

        Returns the subset of ``page_ids`` that the subclass asked to skip.
        Cleanly short-circuits to an empty set when no subclass overrides
        the hook so the default path is identical to pre-hook behavior.

        Per-cluster failures are logged at WARNING and treated as "do not
        skip" (fail open) so a transient dbconfig hiccup never converts
        into a fleet-wide skip.
        """
        if not has_extra_skip:
            return set()

        keep_ids = [cid for cid in page_ids if cid not in page_busy_ids]
        if not keep_ids:
            return set()

        clusters_by_id = {c.id: c for c in Cluster.objects.filter(id__in=keep_ids)}
        skipped_ids: set = set()
        for cluster_id in keep_ids:
            cluster = clusters_by_id.get(cluster_id)
            if cluster is None:
                # Cluster vanished between the candidate scan and now;
                # let the worker-side ``cluster not found`` branch handle
                # logging consistently.
                continue
            try:
                skipped, reason = self.extra_skip_check(cluster)
            except Exception as exc:
                logger.warning(
                    "%s: cluster_id=%s extra_skip_check raised, dispatching anyway: %s",
                    task_name,
                    cluster_id,
                    exc,
                )
                continue
            if skipped:
                skipped_ids.add(cluster_id)
                logger.info(
                    "%s: cluster_id=%s outcome=%s reason=%s",
                    task_name,
                    cluster_id,
                    OUTCOME_SKIPPED,
                    reason,
                )
        return skipped_ids

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
        # Config is the source of truth; _resolve_agent_timeouts only validates
        # and warns on invariant violations. We intentionally do NOT rewrite
        # config_dict so operator-set values propagate unchanged to the worker.
        # The returned ``_invoke_timeout`` is discarded here because the
        # worker reads it back from ``config.agent_invoke_timeout_seconds``
        # inside ``execute_agent_check`` (see the ``ask_agent_with_content``
        # call above); only soft/hard limits need to be passed to
        # ``apply_async`` directly for Celery enforcement.
        _invoke_timeout, soft_time_limit, hard_time_limit = self._resolve_agent_timeouts()
        config_dict = dataclasses.asdict(self.config)
        dispatched_ok = 0
        dispatch_failed = 0
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
                        logger.debug(
                            "%s: cluster_id=%s outcome=%s",
                            task_name,
                            cluster_id,
                            OUTCOME_DISPATCH_DEDUP_SKIPPED,
                        )
                        continue

                countdown = calculate_countdown(count=count, index=idx, duration=DISPATCH_SPREAD_SECONDS)
                celery_task.apply_async(
                    args=[cluster_id, config_dict],
                    countdown=countdown,
                    expires=DISPATCH_INTERVAL_SECONDS,
                    soft_time_limit=soft_time_limit,
                    time_limit=hard_time_limit,
                )
                dispatched_ok += 1
            except Exception as e:
                if lock_key:
                    cache.delete(lock_key)
                dispatch_failed += 1
                logger.error(
                    "%s: cluster_id=%s outcome=%s: %s",
                    task_name,
                    cluster_id,
                    OUTCOME_DISPATCH_FAILED,
                    e,
                )

        logger.info(
            "%s: dispatch_summary requested=%d ok=%d failed=%d dedupe_skipped=%d sample_ids=%s",
            task_name,
            count,
            dispatched_ok,
            dispatch_failed,
            dedupe_skipped,
            cluster_ids[:5] if len(cluster_ids) >= 5 else cluster_ids,
        )
        return dispatched_ok
