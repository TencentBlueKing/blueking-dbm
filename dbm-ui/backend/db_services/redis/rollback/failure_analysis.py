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
AI_ANALYSIS_END_SENTINEL = _("[/AI失败分析]")
FAILED_NODE_LOGS_SENTINEL = _("[子流程失败节点日志]")
AI_ANALYSIS_COUNTDOWN_SECONDS = 60
AI_ANALYSIS_TIMEOUT_SECONDS = 300
# Strips a full markdown code fence (with optional language tag) but never
# touches inline backticks inside the analysis text.
FENCE_RE = re.compile(r"^```[^\n]*\n?|\n?```\s*$")
# task_message embeds the failed-node log block; leave room for timeline + AI block.
_MAX_TASK_MESSAGE_CHARS = 12000
_TASK_MESSAGE_HEAD_CHARS = 4000
_MAX_FLOW_LOG_CHARS = 8000
# Cap embedded logs so MySQL TEXT stays lean and UI remains readable.
_MAX_EMBEDDED_LOG_CHARS = 4000
# Hard caps so we never mirror TaskFlowHandler.get_version_logs (ES size=10000 x2).
_MAX_BKLOG_HITS = 300
_BKLOG_TIME_PAD_HOURS = 24
_ERROR_CONTEXT_LINES = 2
# ERROR levelnames plus message patterns (actuator often embeds errors in INFO lines).
_ERROR_LEVELS = frozenset({"ERROR", "CRITICAL", "FATAL"})
_ERROR_LINE_RE = re.compile(
    "|".join(
        [
            r"Traceback",
            r"Exception",
            r"\[error\]",
            re.escape(_("错误")),
            re.escape(_("失败")),
            r"failed",
            r"Error",
        ]
    ),
    re.I,
)
_OMIT_LINES_PREFIX = _("...(省略")
# Strip wall-clock / epoch timestamps so consecutive heartbeat / retry lines fold.
_NORMALIZE_TS_RE = re.compile(
    r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}"  # 2026-08-10 14:02:52 / 2026/08/10 14:02:52
    r"|\b\d{13}\b"  # epoch millis in job-status JSON
)
_EMBEDDED_TS_RE = re.compile(r"(\d{2}:\d{2}:\d{2})")
_BKLOG_SORT_DESC = [
    ["dtEventTimeStamp", "desc"],
    ["gseIndex", "desc"],
    ["iterationIndex", "desc"],
]

# Stages whose failure evidence lives on a child flow (need BKLog fetch at mark time).
_FLOW_FAILURE_STAGES = (TaskStage.ROLLBACK_FAILED, TaskStage.CLEANUP_FAILED, TaskStage.SCENE_PRESERVED)


def _end_sentinel_for(sentinel: str) -> str:
    """Derive ``[/AI失败分析]`` / ``[/AI分析失败]`` from the opening sentinel."""
    if sentinel.startswith("[") and not sentinel.startswith("[/"):
        return "[" + "/" + sentinel[1:]
    return AI_ANALYSIS_END_SENTINEL


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
    disabled, the report is missing / not in a failed stage, or a successful AI
    analysis block has already been appended (e.g. enqueued at SCENE_PRESERVED and
    later marked terminal again after the DBA completes the confirmation node).
    """
    if not is_exercise_ai_analysis_enabled() or not report_id:
        return False

    try:
        report = Report.objects.filter(id=report_id).only("id", "task_stage", "task_message").first()
        if not report or report.task_stage not in FAILED_STAGES:
            return False
        if AI_ANALYSIS_SENTINEL in (report.task_message or ""):
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
    # Same as CLEANUP_FAILED: rollback-stage preserve has no delete_flow_obj_id yet,
    # so fall back to rollback_flow_obj_id.
    if stage in (TaskStage.CLEANUP_FAILED, TaskStage.SCENE_PRESERVED):
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


def _head_tail_truncate(text: str, max_chars: int, head_chars: int = _TASK_MESSAGE_HEAD_CHARS) -> str:
    """Keep the head (timeline) and tail (embedded child logs); drop the middle."""
    text = text or ""
    if len(text) <= max_chars:
        return text
    head_chars = max(0, min(head_chars, max_chars))
    # Leave room for the middle marker itself.
    marker_budget = 40
    tail_chars = max(0, max_chars - head_chars - marker_budget)
    omitted = len(text) - head_chars - tail_chars
    marker = _("\n...(中间截断 {} 字符)\n").format(omitted)
    return f"{text[:head_chars]}{marker}{text[-tail_chars:]}" if tail_chars else f"{text[:head_chars]}{marker}"


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
    """BKLog search with an explicit size cap; newest-first so tail errors survive heartbeat floods."""
    from backend.components import BKLogApi

    resp = BKLogApi.esquery_search(
        {
            "indices": indices,
            "start_time": start_time,
            "end_time": end_time,
            "query_string": query_string,
            "start": 0,
            "size": size,
            "sort_list": _BKLOG_SORT_DESC,
        }
    )
    return (resp or {}).get("hits", {}).get("hits", []) or []


def _fetch_node_logs_capped(root_id: str, node_id: str, version_id: str, started_at, updated_at) -> list:
    """Fetch node logs from BKLog with hard hit caps; never dump full ES payloads to logs.

    Queries newest-first (desc) so long-running nodes with heartbeat spam still
    return the trailing error lines within the hit budget; results are reversed
    back to chronological order before formatting.
    """
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
        # Desc query already returns newest-first; reverse as a best-effort chrono order.
        hits = list(reversed(hits))

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


def _format_log_line(log) -> str:
    if isinstance(log, dict):
        level = log.get("levelname") or log.get("level") or ""
        message = log.get("message") or ""
        return f"[{level}] {message}".strip() if level else message
    return str(log)


def _normalize_line_for_fold(line: str) -> str:
    """Strip wall-clock / epoch timestamps so consecutive heartbeat/retry lines match."""
    return _NORMALIZE_TS_RE.sub("<TS>", line or "")


def _extract_last_hhmmss(line: str) -> str:
    matches = _EMBEDDED_TS_RE.findall(line or "")
    return matches[-1] if matches else ""


def _fold_consecutive_duplicate_lines(lines: list) -> list:
    """Run-length fold adjacent lines that differ only by timestamps.

    Keeps the first occurrence and appends
    ``（连续重复 N 次，末次 HH:MM:SS）`` so the AI can see flood duration.
    """
    if not lines:
        return []

    folded = []
    i = 0
    n = len(lines)
    while i < n:
        key = _normalize_line_for_fold(lines[i])
        j = i + 1
        last_line = lines[i]
        while j < n and _normalize_line_for_fold(lines[j]) == key:
            last_line = lines[j]
            j += 1
        count = j - i
        if count >= 2:
            last_ts = _extract_last_hhmmss(last_line)
            if last_ts:
                suffix = _("（连续重复 {} 次，末次 {}）").format(count - 1, last_ts)
            else:
                suffix = _("（连续重复 {} 次）").format(count - 1)
            folded.append(f"{lines[i]}{suffix}")
        else:
            folded.append(lines[i])
        i = j
    return folded


def _is_error_line(line: str) -> bool:
    if not line:
        return False
    # Formatted lines start with [LEVEL]; also match message-body patterns.
    if line.startswith("["):
        closing = line.find("]")
        if closing > 1 and line[1:closing].upper() in _ERROR_LEVELS:
            return True
    return bool(_ERROR_LINE_RE.search(line))


def _merge_index_windows(indices: list, total: int, radius: int = _ERROR_CONTEXT_LINES) -> list:
    """Merge overlapping [idx-radius, idx+radius] windows into inclusive ranges."""
    if not indices or total <= 0:
        return []
    ranges = []
    for idx in sorted(indices):
        start = max(0, idx - radius)
        end = min(total - 1, idx + radius)
        if ranges and start <= ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
        else:
            ranges.append((start, end))
    return ranges


def _tail_truncate_line(line: str, max_chars: int) -> str:
    """Keep the useful tail of an oversized line (exception names live at the end).

    Preserves a leading ``[LEVEL]`` tag when present so severity survives truncation.
    """
    if max_chars <= 0:
        # ``line[-0:]`` would return the whole line, not an empty one.
        return ""
    if len(line) <= max_chars:
        return line
    if max_chars <= 3:
        return line[-max_chars:]

    prefix = ""
    body = line
    if line.startswith("["):
        closing = line.find("]")
        if 0 < closing < 20:
            tag = line[: closing + 1]
            # Need room for tag + " ..." + at least one body char.
            if len(tag) + 5 <= max_chars:
                prefix = tag + " "
                body = line[closing + 1 :].lstrip()
                max_chars = max_chars - len(prefix)

    if len(body) <= max_chars:
        return prefix + body
    if max_chars <= 3:
        return prefix + body[-max_chars:]
    return prefix + "..." + body[-(max_chars - 3) :]


def _select_log_lines_for_budget(lines: list, budget: int) -> list:
    """Pick error windows (tail-first) within ``budget`` chars; fall back to pure tail.

    Returns selected lines in chronological order, with ``...(省略 N 行)`` markers
    for gaps. Guarantees the last error line (tail-truncated if needed) fits when
    any error exists.
    """
    if not lines or budget <= 0:
        return []

    # Work on a mutable copy so oversized lines can be tail-truncated in place.
    lines = list(lines)
    error_indices = [i for i, line in enumerate(lines) if _is_error_line(line)]
    if error_indices:
        kept = _kept_indices_error_windows(lines, error_indices, budget)
    else:
        kept = _kept_indices_tail_first(lines, budget)

    ordered = sorted(kept)
    if not ordered:
        return []
    return _render_selected_lines(lines, ordered, set(error_indices), budget)


def _kept_indices_tail_first(lines: list, budget: int) -> list:
    """No-error fallback: keep as many tail lines as fit in ``budget``."""
    kept = []
    length = 0
    for idx in range(len(lines) - 1, -1, -1):
        remaining = budget - length - (1 if kept else 0)
        if remaining <= 0:
            break
        if len(lines[idx]) > remaining:
            if not kept:
                lines[idx] = _tail_truncate_line(lines[idx], remaining)
                kept.append(idx)
            break
        kept.append(idx)
        length += len(lines[idx]) + (1 if length else 0)
    return kept


def _kept_indices_error_windows(lines: list, error_indices: list, budget: int) -> set:
    """Keep merged error windows tail-first; the newest error line is always secured."""
    error_set = set(error_indices)
    kept: set = set()
    length = 0
    for start, end in reversed(_merge_index_windows(error_indices, len(lines))):
        chunk = range(start, end + 1)
        extra = 1 if kept else 0
        chunk_len = sum(len(lines[i]) for i in chunk) + len(chunk) - 1
        if length + chunk_len + extra <= budget:
            kept.update(chunk)
            length += chunk_len + extra
            continue
        _keep_partial_window(lines, kept, length, start, end, error_set, budget)
        break
    return kept


def _keep_partial_window(
    lines: list, kept: set, length: int, start: int, end: int, error_set: set, budget: int
) -> None:
    """Fill a too-big window tail-first, securing its newest error line first.

    Without the upfront reservation, short trailing context lines (err+1, err+2)
    could consume a tight budget and starve the actual error line out.
    """
    last_err = max(i for i in range(start, end + 1) if i in error_set)
    remaining = budget - length - (1 if kept else 0)
    if len(lines[last_err]) > remaining:
        lines[last_err] = _tail_truncate_line(lines[last_err], max(1, remaining))
    kept.add(last_err)
    length += len(lines[last_err]) + (1 if length else 0)

    for idx in range(end, start - 1, -1):
        if idx == last_err:
            continue
        remaining = budget - length - 1
        if remaining <= 0 or len(lines[idx]) > remaining:
            break
        kept.add(idx)
        length += len(lines[idx]) + 1


def _render_selected_lines(lines: list, ordered: list, error_set: set, budget: int) -> list:
    """Render kept indices chronologically, inserting omission markers for gaps."""
    result = []
    length = 0
    prev = None

    if ordered[0] > 0:
        marker = _("...(省略 {} 行)").format(ordered[0])
        if len(marker) <= budget:
            result.append(marker)
            length = len(marker)

    for idx in ordered:
        line = lines[idx]
        if prev is not None and idx > prev + 1:
            marker = _("...(省略 {} 行)").format(idx - prev - 1)
            marker_cost = len(marker) + (1 if result else 0)
            line_cost = len(line) + 1
            if length + marker_cost + line_cost <= budget:
                result.append(marker)
                length += marker_cost
        cost = len(line) + (1 if result else 0)
        if length + cost > budget:
            remaining = budget - length - (1 if result else 0)
            has_content = any(not x.startswith(_OMIT_LINES_PREFIX) for x in result)
            # Force-fit error lines; for pure-tail, only force-fit when nothing
            # useful is kept yet. Otherwise drop the leftover non-error line.
            if remaining > 0 and (idx in error_set or not has_content):
                result.append(_tail_truncate_line(line, remaining))
            break
        result.append(line)
        length += cost
        prev = idx

    return result


def get_last_failed_node_logs(root_id: str, max_chars: int = _MAX_FLOW_LOG_CHARS) -> str:
    """Locate the last abnormal node under ``root_id`` and return its logs (capped).

    DB: indexed ``FlowNode`` lookup by ``root_id`` (+ optional pipeline tree for
    node name). Never scans unscoped tables.

    Logs: capped BKLog queries (newest-first so heartbeat spam cannot hide the
    trailing error). Lines are fold-deduped, then error-window selected
    (tail-first) within ``max_chars``.
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

    header = (
        f"failed_node: {node_name} ({node_id}) version={version_id} "
        f"status={getattr(last_failed, 'status', '')} pick={pick_reason}"
    )
    body_budget = max(0, max_chars - len(header) - (1 if max_chars > len(header) else 0))
    formatted = [_format_log_line(log) for log in logs]
    folded = _fold_consecutive_duplicate_lines(formatted)
    selected = _select_log_lines_for_budget(folded, body_budget)
    parts = [header, *selected]
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

    end_sentinel = _end_sentinel_for(sentinel)
    ts = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    # Blank lines around the block keep it visually distinct even when cleanup
    # logs are later merged after it.
    block_text = f"\n{sentinel} {ts}\n{cleaned}\n{end_sentinel}\n"
    combined = f"{existing.rstrip()}{block_text}".strip()
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
    task_message = _head_tail_truncate(report.task_message or "", _MAX_TASK_MESSAGE_CHARS)

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
