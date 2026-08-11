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
import json
import logging
import re
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from celery.schedules import crontab
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.core.notify.handlers import CmsiHandler
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_report.enums import REDIS_ROLLBACK_EXER_FAILED_STAGES as FAILED_STAGES
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.db_report.models.ai_analysis_report import AiAnalysisReport, ResultFormat
from backend.db_services.redis.autofix.enums import MsgPriority
from backend.db_services.redis.autofix.message import load_chat_ids_by_priority
from backend.db_services.redis.rollback.failure_analysis import (
    AI_ANALYSIS_END_SENTINEL,
    AI_ANALYSIS_SENTINEL,
    is_exercise_ai_analysis_enabled,
)
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")

WEEKLY_SUMMARY_AGENT = DBMAgentCode.REDIS_EXERCISE_ANALYST.value
WEEKLY_SUMMARY_TIMEOUT_SECONDS = 600
MAX_FAILURE_CASES = 50
MAX_WECOM_CONTENT_CHARS = 1024
CATEGORY_PATTERN = re.compile(r"原因分类\s*[:：]\s*([^\n\r]+)")
DIAGNOSIS_PATTERN = re.compile(r"诊断\s*[:：]\s*([^\n\r]+)")
_MAX_CASE_DIAGNOSIS_CHARS = 120
# Legacy AI blocks (no end sentinel) are short by contract (≤5 content lines);
# an 8-line window keeps cleanup logs that follow from polluting the parse.
_LEGACY_AI_BLOCK_MAX_LINES = 8


def get_week_window(now: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Return [last Sunday 12:00, this Sunday 12:00).

    Reports are created Sun 12:00 (candidate init). The weekly summary runs
    Monday 10:00, so the start picks up the batch created last Sunday (the
    week just exercised) and the end cuts off this Sunday's batch, which
    belongs to the upcoming week.
    """
    now = now or timezone.now()
    local_now = timezone.localtime(now)
    # weekday(): Mon=0 ... Sun=6
    days_since_sunday = (local_now.weekday() + 1) % 7
    this_sunday = (local_now - timedelta(days=days_since_sunday)).replace(hour=12, minute=0, second=0, microsecond=0)
    # If we are before Sunday 12:00 today, the last full batch is two Sundays back.
    if local_now < this_sunday:
        this_sunday = this_sunday - timedelta(days=7)
    return this_sunday - timedelta(days=7), this_sunday


def get_previous_week_window(start: datetime, end: datetime) -> Tuple[datetime, datetime]:
    """Previous window of equal length ending at ``start``."""
    delta = end - start
    return start - delta, start


def _extract_last_ai_block(task_message: str) -> str:
    """Return the body of the last ``[AI失败分析]`` block, excluding sentinels.

    Prefer an explicit ``[/AI失败分析]`` end marker. For legacy reports without
    one, take at most ``_LEGACY_AI_BLOCK_MAX_LINES`` lines after the opening
    sentinel so later cleanup logs cannot pollute category/diagnosis parsing.
    """
    if not task_message or AI_ANALYSIS_SENTINEL not in task_message:
        return ""

    start = task_message.rfind(AI_ANALYSIS_SENTINEL)
    if start < 0:
        return ""

    after_open = task_message[start + len(AI_ANALYSIS_SENTINEL) :]
    # Drop the optional timestamp on the sentinel line (" 2026-08-10 14:43:43\n...")
    if after_open.startswith(" ") or after_open.startswith("\t"):
        nl = after_open.find("\n")
        after_open = after_open[nl + 1 :] if nl >= 0 else ""
    elif after_open.startswith("\n"):
        after_open = after_open[1:]

    end = after_open.find(AI_ANALYSIS_END_SENTINEL)
    if end >= 0:
        return after_open[:end].strip()

    # Legacy: no end sentinel — take a short fixed window.
    lines = after_open.splitlines()
    return "\n".join(lines[:_LEGACY_AI_BLOCK_MAX_LINES]).strip()


def _parse_failure_category(task_message: str) -> str:
    block = _extract_last_ai_block(task_message)
    if not block:
        return _("未分析")
    matches = CATEGORY_PATTERN.findall(block)
    if not matches:
        return _("未分类")
    return matches[-1].strip() or _("未分类")


def _parse_failure_diagnosis(task_message: str) -> str:
    """Extract the last AI ``诊断`` line; empty when analysis is missing."""
    block = _extract_last_ai_block(task_message)
    if not block:
        return ""
    matches = DIAGNOSIS_PATTERN.findall(block)
    if not matches:
        return ""
    return matches[-1].strip()


def _reports_in_window(start: datetime, end: datetime) -> QuerySet:
    return Report.objects.filter(create_at__gte=start, create_at__lt=end)


def aggregate_exercise_stats(start: datetime, end: datetime) -> Dict:
    """Deterministic aggregates for the weekly agent. Never let the LLM count."""
    qs = _reports_in_window(start, end)
    total = qs.count()
    done = qs.filter(task_stage=TaskStage.DONE).count()
    skipped = qs.filter(task_stage=TaskStage.SKIPPED).count()
    failed_qs = qs.filter(task_stage__in=FAILED_STAGES)
    failed = failed_qs.count()
    success_rate = round((done / total) * 100, 1) if total else 0.0

    stage_counter: Counter = Counter()
    type_counter: Counter = Counter()
    biz_counter: Counter = Counter()
    category_counter: Counter = Counter()
    cluster_fail_counter: Counter = Counter()
    missing_analysis = 0
    failure_cases: List[str] = []

    for report in failed_qs.iterator():
        stage_counter[str(report.task_stage)] += 1
        type_counter[report.cluster_type or "unknown"] += 1
        biz_counter[str(report.bk_biz_id)] += 1
        category = _parse_failure_category(report.task_message or "")
        category_counter[category] += 1
        if category == _("未分析"):
            missing_analysis += 1
        cluster_fail_counter[report.cluster_domain or str(report.cluster_id)] += 1
        if len(failure_cases) < MAX_FAILURE_CASES:
            instance = ""
            if report.instance_ip:
                instance = f"{report.instance_ip}:{report.instance_port or ''}"
            diagnosis = _parse_failure_diagnosis(report.task_message or "")
            line = f"{report.cluster_domain or '-'} {instance or '-'} {report.task_stage} {category}"
            if diagnosis:
                line += f" | {diagnosis[:_MAX_CASE_DIAGNOSIS_CHARS]}"
            failure_cases.append(line)

    repeat_offenders = [
        {"cluster_domain": domain, "fail_count": count}
        for domain, count in cluster_fail_counter.most_common()
        if count >= 2
    ]

    return {
        "total": total,
        "done": done,
        "skipped": skipped,
        "failed": failed,
        "success_rate_pct": success_rate,
        "failed_stage_distribution": dict(stage_counter),
        "failed_cluster_type_distribution": dict(type_counter),
        "failed_biz_top": dict(biz_counter.most_common(10)),
        "failure_category_distribution": dict(category_counter),
        "repeat_offender_clusters": repeat_offenders[:20],
        "missing_analysis_count": missing_analysis,
        "failure_cases": failure_cases,
    }


def build_week_over_week_delta(current: Dict, previous: Dict) -> Dict:
    keys = ("total", "done", "failed", "skipped", "success_rate_pct")
    return {key: round(current.get(key, 0) - previous.get(key, 0), 1) for key in keys}


def cut_content(content: str, max_len: int = MAX_WECOM_CONTENT_CHARS) -> List[str]:
    """Split content into chunks that strictly fit the WeCom robot limit."""
    if max_len <= 0:
        raise ValueError("max_len must be greater than zero")

    chunks: List[str] = []
    current = ""
    for segment in content.splitlines(keepends=True):
        while segment:
            available = max_len - len(current)
            current += segment[:available]
            segment = segment[available:]
            if len(current) == max_len:
                chunks.append(current)
                current = ""

    if current or not chunks:
        chunks.append(current)
    return chunks


def build_share_url(report_id: str) -> str:
    return f"{env.BK_SAAS_HOST.rstrip('/')}/ai-chat/share/{report_id}/"


def persist_weekly_ai_report(title: str, summary: str, markdown: str) -> AiAnalysisReport:
    report = AiAnalysisReport(
        ai_agent=WEEKLY_SUMMARY_AGENT,
        format=ResultFormat.MARKDOWN.value,
        bk_biz_id=0,
        cluster_domain="",
        title=title,
        summary=summary,
        creator="system",
    )
    report.set_content(markdown)
    report.save()
    return report


def format_wecom_headline(stats: Dict, delta: Dict, share_url: str, window_label: str) -> str:
    lines = [
        _("【DBM】Redis回档演练周报"),
        window_label,
        _("总量: {} | 成功: {} ({:.1f}%) | 失败: {} | 跳过: {}").format(
            stats["total"],
            stats["done"],
            stats["success_rate_pct"],
            stats["failed"],
            stats["skipped"],
        ),
        _("较上周: 总量{:+} / 失败{:+} / 成功率{:+.1f}%").format(
            delta.get("total", 0),
            delta.get("failed", 0),
            delta.get("success_rate_pct", 0),
        ),
        _("未分析失败: {}").format(stats.get("missing_analysis_count", 0)),
    ]
    if stats.get("failure_category_distribution"):
        top_cats = list(stats["failure_category_distribution"].items())[:5]
        cat_text = ", ".join(f"{name}:{count}" for name, count in top_cats)
        lines.append(_("原因Top: {}").format(cat_text))
    if share_url:
        lines.append(_("详情: {}").format(share_url))
    return "\n".join(lines)


def send_weekly_summary_to_qywx(content: str) -> bool:
    chat_ids = load_chat_ids_by_priority(MsgPriority.L1.value)
    if not chat_ids:
        logger.info("no L1 chat ids configured for redis rollback exercise weekly summary, skip send")
        return False
    title = _("【DBM】Redis回档演练周报")
    for chunk in cut_content(content):
        CmsiHandler(title, chunk, chat_ids).send_wecom_robot()
    return True


def run_weekly_ai_summary(now: Optional[datetime] = None) -> Optional[str]:
    """Aggregate the week, ask the agent, persist AiAnalysisReport, push WeCom."""
    if not is_exercise_ai_analysis_enabled():
        logger.info("redis rollback exercise AI analysis disabled, skip weekly summary")
        return None

    start, end = get_week_window(now)
    prev_start, prev_end = get_previous_week_window(start, end)
    stats = aggregate_exercise_stats(start, end)
    prev_stats = aggregate_exercise_stats(prev_start, prev_end)
    delta = build_week_over_week_delta(stats, prev_stats)

    window_label = f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%Y-%m-%d %H:%M')}"
    stats_for_agent = {
        **{k: v for k, v in stats.items() if k != "failure_cases"},
        "week_over_week_delta": delta,
        "previous_window": {
            "total": prev_stats["total"],
            "done": prev_stats["done"],
            "failed": prev_stats["failed"],
            "skipped": prev_stats["skipped"],
            "success_rate_pct": prev_stats["success_rate_pct"],
        },
    }
    failure_cases_text = "\n".join(stats.get("failure_cases") or []) or _("(本周无失败样例)")

    from backend.dbm_aiagent.agent.commands.redis_commands import SummarizeRedisRollbackExerciseWeek
    from backend.dbm_aiagent.agent.handlers import AgentHandler

    elapsed = None
    started = time.monotonic()
    try:
        markdown = AgentHandler.ask_agent_with_command(
            command=SummarizeRedisRollbackExerciseWeek.command,
            command_params={
                "window": window_label,
                "stats_json": json.dumps(stats_for_agent, ensure_ascii=False, indent=2),
                "failure_cases": failure_cases_text,
            },
            timeout=WEEKLY_SUMMARY_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - started
    except Exception:
        logger.exception(
            "redis rollback exercise weekly AI summary agent call failed ai_cost=%.1fs",
            time.monotonic() - started,
        )
        markdown = _(
            "# Redis回档演练周报\n\n智能体调用失败，以下为系统统计摘要。\n\n"
            "- 窗口: {window}\n"
            "- 总量/成功/失败/跳过: {total}/{done}/{failed}/{skipped}\n"
            "- 成功率: {rate}%\n"
        ).format(
            window=window_label,
            total=stats["total"],
            done=stats["done"],
            failed=stats["failed"],
            skipped=stats["skipped"],
            rate=stats["success_rate_pct"],
        )

    iso_week = timezone.localtime(end).strftime("%G-W%V")
    title = _("Redis回档演练周报 {}").format(iso_week)
    summary = _("总量{} 成功{:.1f}% 失败{}").format(stats["total"], stats["success_rate_pct"], stats["failed"])
    if elapsed is not None:
        summary = f"{summary} AI耗时:{elapsed:.1f}s"
    ai_report = persist_weekly_ai_report(title=title, summary=summary, markdown=markdown or "")
    share_url = build_share_url(str(ai_report.id))

    headline = format_wecom_headline(stats, delta, share_url, window_label)
    try:
        send_weekly_summary_to_qywx(headline)
    except Exception:
        logger.exception("failed to push redis rollback exercise weekly summary to WeCom")

    logger.info(
        "redis rollback exercise weekly summary done: report_id=%s total=%s failed=%s share=%s ai_cost=%s",
        ai_report.id,
        stats["total"],
        stats["failed"],
        share_url,
        f"{elapsed:.1f}s" if elapsed is not None else "n/a",
    )
    return str(ai_report.id)


# Runs after the batch week ends (Sun 12:00 candidate init); Monday 10:00 gives
# room for weekend repair marks while the window cutoff (this Sunday 12:00) keeps
# the upcoming week's reports out.
@register_periodic_task(run_every=crontab(day_of_week="1", hour="10", minute="0"))
def redis_rollback_exercise_weekly_ai_summary():
    """Monday 10:00 weekly AI digest for Redis rollback exercise."""
    run_weekly_ai_summary()
