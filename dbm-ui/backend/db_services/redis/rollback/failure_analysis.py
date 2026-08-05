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
import time

from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.db_report.enums import REDIS_ROLLBACK_EXER_FAILED_STAGES as FAILED_STAGES
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report

logger = logging.getLogger("root")

AI_ANALYSIS_SENTINEL = _("[AI失败分析]")
AI_ANALYSIS_FAILED_SENTINEL = _("[AI分析失败]")
FAILED_NODE_LOGS_SENTINEL = _("[子流程失败节点日志]")
AI_ANALYSIS_COUNTDOWN_SECONDS = 60
AI_ANALYSIS_TIMEOUT_SECONDS = 300
# Strips a full markdown code fence (with optional language tag) but never
# touches inline backticks inside the analysis text.
FENCE_RE = re.compile(r"^```[^\n]*\n?|\n?```\s*$")
# task_message embeds the failed-node log block; leave room for timeline + AI block.
_MAX_TASK_MESSAGE_CHARS = 12000
_MAX_FLOW_LOG_CHARS = 8000
# Cap embedded logs so MySQL TEXT stays lean and UI remains readable.
_MAX_EMBEDDED_LOG_CHARS = 4000
# Hard caps so we never mirror TaskFlowHandler.get_version_logs (ES size=10000 x2).
_MAX_BKLOG_HITS = 300
_BKLOG_TIME_PAD_HOURS = 24

# Stages whose failure evidence lives on a child flow (need BKLog fetch at mark time).
_FLOW_FAILURE_STAGES = (TaskStage.ROLLBACK_FAILED, TaskStage.CLEANUP_FAILED)


def is_exercise_ai_analysis_enabled() -> bool:
    """Return True when both global AI and exercise-level AI analysis are on."""
    if not env.ENABLE_DBM_AI:
        return False
    try:
        from backend.db_services.redis.rollback.config import RedisRollbackExerciseConfig

        return bool(RedisRollbackExerciseConfig.from_settings().ai_analysis_enabled)
    except Exception:
        logger.exception("failed to load RedisRollbackExerciseConfig.ai_analysis_enabled")
        return False


def enqueue_exercise_failure_analysis(report_id: int, countdown: int = AI_ANALYSIS_COUNTDOWN_SECONDS) -> bool:
    """Fire an async AI analysis only when the report is confirmed failed.

    Safe to call from ``Report.mark()``: never raises. No-ops when AI analysis is
    disabled or the report is missing / not in a failed stage.
    """
    if not is_exercise_ai_analysis_enabled() or not report_id:
        return False

    try:
        report = Report.objects.filter(id=report_id).only("id", "task_stage").first()
        if not report or report.task_stage not in FAILED_STAGES:
            return False

        analyze_redis_rollback_exercise_failure.apply_async(
            args=(report_id,),
            countdown=max(0, int(countdown)),
        )
        logger.info(
            "enqueued redis rollback exercise AI analysis for report %s countdown=%ss",
            report_id,
            max(0, int(countdown)),
        )
        return True
    except Exception:
        logger.exception("failed to enqueue redis rollback exercise AI analysis for report %s", report_id)
        return False


def _resolve_flow_root_id(report: Report, stage=None) -> str:
    """Pick the child flow root_id whose logs are most relevant.

    ``stage`` defaults to ``report.task_stage``. Pass the stage that is about
    to be applied when embedding logs before ``mark()`` persists it.
    """
    stage = stage if stage is not None else report.task_stage
    if stage == TaskStage.CLEANUP_FAILED:
        return report.delete_flow_obj_id or report.rollback_flow_obj_id or ""
    if stage == TaskStage.ROLLBACK_FAILED:
        return report.rollback_flow_obj_id or ""
    return ""


def embed_failed_node_logs(task_message: str, report: Report, stage) -> str:
    """Append an indented failed-node log block for flow-failure stages.

    Never raises. Idempotent when ``FAILED_NODE_LOGS_SENTINEL`` is already
    present. No-ops for non-flow stages, missing root_id, empty logs, or
    BKLog / FlowNode errors (returns the original ``task_message``).
    """
    if stage not in _FLOW_FAILURE_STAGES:
        return task_message or ""

    existing = task_message or ""
    if FAILED_NODE_LOGS_SENTINEL in existing:
        return existing

    try:
        root_id = _resolve_flow_root_id(report, stage=stage)
        if not root_id:
            return existing

        logs = get_last_failed_node_logs(root_id, max_chars=_MAX_EMBEDDED_LOG_CHARS)
        if not logs:
            return existing

        indented = "\n".join(f"    {line}" for line in logs.splitlines())
        block = f"{FAILED_NODE_LOGS_SENTINEL} root_id={root_id}\n{indented}"
        return f"{existing.rstrip()}\n{block}".strip() if existing.strip() else block
    except Exception:
        logger.exception(
            "failed to embed child flow logs for report %s stage=%s",
            getattr(report, "id", None),
            stage,
        )
        return existing


def _truncate_text(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...(truncated)"


def _find_activity_name(activities: dict, target_node_id: str) -> str:
    """DFS for a single node name; stop early (avoid building a full name map)."""
    for act_id, activity in (activities or {}).items():
        if act_id == target_node_id:
            return activity.get("name") or ""
        if "pipeline" in activity:
            nested = _find_activity_name(activity["pipeline"].get("activities", {}), target_node_id)
            if nested:
                return nested
    return ""


def _esquery_search_capped(indices: str, query_string: str, start_time: str, end_time: str, size: int) -> list:
    """BKLog search with an explicit size cap (TaskFlowHandler hardcodes 10000)."""
    from backend.components import BKLogApi

    resp = BKLogApi.esquery_search(
        {
            "indices": indices,
            "start_time": start_time,
            "end_time": end_time,
            "query_string": query_string,
            "start": 0,
            "size": size,
        }
    )
    return (resp or {}).get("hits", {}).get("hits", []) or []


def _fetch_node_logs_capped(root_id: str, node_id: str, version_id: str, started_at, updated_at) -> list:
    """Fetch node logs from BKLog with hard hit caps; never dump full ES payloads to logs."""
    from datetime import timedelta

    from backend.db_services.taskflow.handlers import TaskFlowHandler
    from backend.utils.time import datetime2str

    if not started_at and not updated_at:
        return []

    start_dt = started_at or updated_at
    end_dt = (updated_at or started_at) + timedelta(hours=_BKLOG_TIME_PAD_HOURS)
    start_time = datetime2str(start_dt)
    end_time = datetime2str(end_dt)

    # Prefer dbactuator (rollback drill failures are usually here); keep a smaller
    # worker-log window. Combined hit budget stays at _MAX_BKLOG_HITS.
    actuator_size = min(_MAX_BKLOG_HITS, 250)
    worker_size = min(_MAX_BKLOG_HITS - actuator_size, 50)
    query = f'"{root_id}" AND "{node_id}" AND {version_id}'

    hits = []
    try:
        hits.extend(
            _esquery_search_capped(
                indices=f"{env.DBA_APP_BK_BIZ_ID}_bklog.dbm_dbactuator,{env.DBA_APP_BK_BIZ_ID}_bklog.dbm_win_dbactuator,",
                query_string=query,
                start_time=start_time,
                end_time=end_time,
                size=actuator_size,
            )
        )
    except Exception:
        logger.exception("bklog dbactuator query failed root_id=%s node_id=%s", root_id, node_id)

    if worker_size > 0:
        try:
            hits.extend(
                _esquery_search_capped(
                    indices=f"{env.DBA_APP_BK_BIZ_ID}_bklog.dbm_log",
                    query_string=query,
                    start_time=start_time,
                    end_time=end_time,
                    size=worker_size,
                )
            )
        except Exception:
            logger.exception("bklog dbm_log query failed root_id=%s node_id=%s", root_id, node_id)

    if not hits:
        return []

    try:
        hits.sort(
            key=lambda x: (
                int(x["_source"]["dtEventTimeStamp"]),
                int(x["_source"]["gseIndex"]),
                int(x["_source"]["iterationIndex"]),
            )
        )
    except Exception:
        pass

    logs = []
    for hit in hits:
        try:
            source = hit["_source"]
            formatted = TaskFlowHandler._format_log(source["log"], source["serverIp"], hit["_index"])
            if not formatted:
                continue
            logs.append(
                TaskFlowHandler.generate_log_record(
                    timestamp=source.get("time"),
                    levelname=formatted["levelname"],
                    message=formatted["log"],
                )
            )
        except Exception:
            continue
    return logs


def _pick_last_abnormal_flow_node(root_id: str):
    """Pick the last node that did not finish normally.

    Terminated tickets usually leave the stopping node as ``REVOKED``, not
    ``FAILED``. Prefer ``FAILED_STATES`` (FAILED/REVOKED); fall back to the
    latest started non-FINISHED node (covers stuck RUNNING after revoke races).
    """
    from backend.flow.consts import FAILED_STATES, SUCCEED_STATES
    from backend.flow.models import FlowNode

    # unique_together (root_id, node_id, version_id) → root_id prefix index
    qs = FlowNode.objects.filter(root_id=root_id).only("node_id", "version_id", "started_at", "updated_at", "status")
    node = qs.filter(status__in=FAILED_STATES).order_by("-updated_at").first()
    if node:
        return node, "failed_or_revoked"
    node = qs.exclude(status__in=SUCCEED_STATES).exclude(started_at__isnull=True).order_by("-updated_at").first()
    if node:
        return node, "started_not_finished"
    return None, ""


def get_last_failed_node_logs(root_id: str, max_chars: int = _MAX_FLOW_LOG_CHARS) -> str:
    """Locate the last abnormal node under ``root_id`` and return its logs (capped).

    DB: indexed ``FlowNode`` lookup by ``root_id`` (+ optional pipeline tree for
    node name). Never scans unscoped tables.

    Logs: capped BKLog queries (not ``get_version_logs``, which uses size=10000×2
    and dumps full ES payloads into app logs). Text is truncated to ``max_chars``.
    """
    if not root_id:
        return ""

    from backend.flow.engine.bamboo.engine import BambooEngine

    last_failed, pick_reason = _pick_last_abnormal_flow_node(root_id)
    if not last_failed:
        return ""

    node_id = last_failed.node_id
    version_id = last_failed.version_id

    node_name = ""
    try:
        tree = BambooEngine(root_id=root_id).get_pipeline_tree() or {}
        node_name = _find_activity_name(tree.get("activities", {}), node_id)
    except Exception:
        logger.exception("failed to resolve node name for root_id=%s node_id=%s", root_id, node_id)

    logs = _fetch_node_logs_capped(
        root_id=root_id,
        node_id=node_id,
        version_id=version_id,
        started_at=last_failed.started_at,
        updated_at=last_failed.updated_at,
    )

    # Build text incrementally and stop once we exceed max_chars (avoid joining
    # a huge in-memory list then slicing).
    header = (
        f"failed_node: {node_name} ({node_id}) version={version_id} "
        f"status={getattr(last_failed, 'status', '')} pick={pick_reason}"
    )
    parts = [header]
    length = len(header)
    for log in logs:
        if isinstance(log, dict):
            level = log.get("levelname") or log.get("level") or ""
            message = log.get("message") or ""
            line = f"[{level}] {message}".strip() if level else message
        else:
            line = str(log)
        if length + 1 + len(line) > max_chars:
            parts.append("...(truncated)")
            break
        parts.append(line)
        length += 1 + len(line)

    return "\n".join(parts).strip()


def _append_block_to_report(report: Report, sentinel: str, block: str, elapsed_seconds: float = None) -> None:
    """Append a sentinel-tagged block to ``report.task_message`` without re-triggering
    failure enqueue (stage=None). Idempotent per sentinel."""
    cleaned = (block or "").strip()
    if cleaned.startswith("```"):
        cleaned = FENCE_RE.sub("", cleaned).strip()

    if elapsed_seconds is not None:
        cleaned = f"{cleaned}\n{_('AI耗时')}: {elapsed_seconds:.1f}s"

    existing = report.task_message or ""
    if sentinel in existing:
        return

    ts = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    combined = f"{existing.rstrip()}\n{sentinel} {ts}\n{cleaned}".strip()
    report.mark(task_message=combined)


def _append_analysis_to_report(report: Report, ai_response: str, elapsed_seconds: float = None) -> None:
    """Append the AI analysis block (``AI_ANALYSIS_SENTINEL``)."""
    cleaned = (ai_response or "").strip()
    if not cleaned:
        cleaned = _("原因分类: 其他\n诊断: 智能体未返回有效内容\n建议: 人工查看任务日志")
    _append_block_to_report(report, AI_ANALYSIS_SENTINEL, cleaned, elapsed_seconds)


def _append_analysis_failed_to_report(report: Report, elapsed_seconds: float = None) -> None:
    """Mark the report as "AI analysis failed" with a distinct sentinel so weekly
    stats count it as 未分析 instead of a real category."""
    _append_block_to_report(
        report,
        AI_ANALYSIS_FAILED_SENTINEL,
        _("诊断: 智能体调用失败\n建议: 人工查看任务日志"),
        elapsed_seconds,
    )


@shared_task(
    name=(
        "backend.db_periodic_task.local_tasks.redis_backup_rollback.failure_analysis."
        "analyze_redis_rollback_exercise_failure"
    )
)
def analyze_redis_rollback_exercise_failure(report_id: int) -> None:
    """Analyze a single failed rollback-exercise report and append a short diagnosis."""
    report = (
        Report.objects.filter(id=report_id)
        .only(
            "id",
            "task_stage",
            "task_message",
            "cluster_domain",
            "cluster_type",
            "instance_ip",
            "instance_port",
            "redis_version",
        )
        .first()
    )
    if not report:
        logger.warning("redis rollback exercise AI analysis skipped: report %s not found", report_id)
        return

    if report.task_stage not in FAILED_STAGES:
        logger.info(
            "redis rollback exercise AI analysis skipped: report %s stage=%s not failed",
            report_id,
            report.task_stage,
        )
        return

    if AI_ANALYSIS_SENTINEL in (report.task_message or ""):
        logger.info("redis rollback exercise AI analysis skipped: report %s already analyzed", report_id)
        return

    # Failed-node logs are already embedded into task_message at mark time
    # (see embed_failed_node_logs); do not re-fetch from BKLog here.
    task_message = report.task_message or ""
    if len(task_message) > _MAX_TASK_MESSAGE_CHARS:
        task_message = task_message[:_MAX_TASK_MESSAGE_CHARS] + "\n...(truncated)"

    instance = ""
    if report.instance_ip:
        instance = f"{report.instance_ip}:{report.instance_port or ''}"

    from backend.dbm_aiagent.agent.commands.redis_commands import AnalyzeRedisRollbackExerciseFailure
    from backend.dbm_aiagent.agent.handlers import AgentHandler

    started = time.monotonic()
    try:
        ai_response = AgentHandler.ask_agent_with_command(
            command=AnalyzeRedisRollbackExerciseFailure.command,
            command_params={
                "cluster_domain": report.cluster_domain or "",
                "cluster_type": report.cluster_type or "",
                "instance": instance,
                "redis_version": report.redis_version or "",
                "task_stage": str(report.task_stage or ""),
                "task_message": task_message,
            },
            timeout=AI_ANALYSIS_TIMEOUT_SECONDS,
        )
    except Exception:
        elapsed = time.monotonic() - started
        logger.exception(
            "redis rollback exercise AI analysis failed for report %s ai_cost=%.1fs",
            report_id,
            elapsed,
        )
        _append_analysis_failed_to_report(report, elapsed_seconds=elapsed)
        return

    elapsed = time.monotonic() - started
    _append_analysis_to_report(report, ai_response, elapsed_seconds=elapsed)
    logger.info(
        "redis rollback exercise AI analysis appended for report %s ai_cost=%.1fs",
        report_id,
        elapsed,
    )
