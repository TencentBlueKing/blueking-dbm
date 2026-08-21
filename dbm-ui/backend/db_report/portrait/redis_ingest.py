# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License as distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
the specific language governing permissions and limitations under the License.

Redis 集群画像摘要上报助手。

职责：
    - 按集群聚合巡检消息，带检查项前缀写入画像摘要表
    - 吞掉 SDK / ORM 异常，绝不阻断巡检主流程

注入策略（每日注入）：
    - 每个 (集群, 子检查前缀) 每天产一条摘要，**正常态也写**：
      组内存在告警/异常行时只写这些行的消息；全部正常时写一条固定的正常文案，
      避免把 N 条实例级 "ok" 拼进摘要。
    - 因此「时间窗内无摘要」的语义是「当天巡检未执行或未覆盖该集群」，
      不再是「健康」。消费侧口径见 redis_dimensions._DESCRIPTIONS 与
      redis-portrait-generator skill 的判读规则。

边界：
    - 只接 daily 巡检源，一天一条，因此不做写入节流；如需接入高频源（一天多次），
      必须先补节流，否则会压垮画像摘要的信噪比。
    - 本表纯追加、无当天去重：巡检任务重跑会在同一天留下重复行（已知取舍）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_report.enums import ReportStateType
from backend.db_report.portrait.exceptions import PortraitSDKBaseException
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.sdk import PortraitIngestSDK, ingest_summary

logger = logging.getLogger("root")

# prefix_by_subtype miss 时的兜底前缀：写入维度摘要，避免静默跳过被消费侧判成巡检缺口。
UNMAPPED_SUBTYPE_PREFIX = _("[未映射]")
MAX_MSGS_PER_SUMMARY = 8
# 单条消息上限：8 条 + 前缀 + 「等共 N 项」仍远低于 SDK 4000 字符硬顶，避免硬切把尾巴截掉。
_MAX_MSG_CHARS = 400
# 与 weekly_ai_summary._extract_last_ai_block 对齐：无结束标记时最多取 8 行。
_LEGACY_AI_BLOCK_MAX_LINES = 8
_ROLLBACK_FALLBACK_CHARS = 800


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _truncate(text: str, limit: int) -> str:
    if not text or len(text) <= limit:
        return text or ""
    return text[:limit]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _cluster_identity(row: Any) -> Tuple[str, int]:
    cluster = _row_get(row, "cluster")
    if cluster is not None and hasattr(cluster, "immute_domain"):
        return str(cluster.immute_domain or ""), _safe_int(getattr(cluster, "bk_biz_id", None))
    domain = cluster or _row_get(row, "cluster_domain") or ""
    return str(domain), _safe_int(_row_get(row, "bk_biz_id"))


def _is_normal_state(state: Any) -> bool:
    return _enum_value(state) == ReportStateType.NORMAL.value


def _build_summary(prefix: str, messages: List[str]) -> str:
    clipped = [_truncate(m, _MAX_MSG_CHARS) for m in messages]
    if len(clipped) > MAX_MSGS_PER_SUMMARY:
        clipped = clipped[:MAX_MSGS_PER_SUMMARY] + [_("等共 {n} 项").format(n=len(messages))]
    return f"{prefix} " + "；".join(clipped)


def ingest_redis_cluster_summary(
    *,
    cluster_domain: str,
    bk_biz_id: int,
    dimension: RedisPortraitDimensionCode,
    prefix: str,
    messages: List[str],
    detail_url: str = "",
) -> None:
    """按集群写入一条画像摘要。messages 为空时不写。失败只记日志，绝不外抛。"""
    try:
        if not messages:
            return

        summary = _build_summary(prefix, [m for m in messages if m])
        ingest_summary(
            db_type=DBType.Redis,
            dimension=dimension,
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            report_time=timezone.now(),
            summary=_truncate(summary, PortraitIngestSDK.MAX_SUMMARY_CHARS),
            detail_url=_truncate(detail_url or "", PortraitIngestSDK.MAX_DETAIL_URL_CHARS),
        )
    except PortraitSDKBaseException:
        logger.exception(
            "redis portrait ingest sdk failed: domain=%s dim=%s prefix=%s",
            cluster_domain,
            getattr(dimension, "value", dimension),
            prefix,
        )
    except Exception:  # noqa
        logger.exception(
            "redis portrait ingest failed: domain=%s dim=%s prefix=%s",
            cluster_domain,
            getattr(dimension, "value", dimension),
            prefix,
        )


def ingest_daily_cluster_rows(
    rows: Iterable[Any],
    *,
    dimension: RedisPortraitDimensionCode,
    prefix: Optional[str] = None,
    prefix_by_subtype: Optional[Dict[str, str]] = None,
    detail_url: str = "",
) -> None:
    """把实例级巡检行按集群（及可选 subtype）聚合成每日画像摘要。

    每个 (集群, 子检查前缀) 产一条：组内有告警/异常行时只写这些行的消息，
    全部正常时写一条固定的正常文案。正常行只用来占位分组，其 msg（通常是 "ok"）不入摘要。

    prefix_by_subtype 未命中时不静默丢弃：打 warning，并以 [未映射] 前缀写入摘要（含 subtype），
    避免消费侧把漏配误判成巡检缺口或健康。
    """
    try:
        # 用普通 dict 而非 set 收集分组，保证写入顺序与巡检行顺序一致，便于排查
        grouped: Dict[Tuple[str, int, str], List[str]] = {}
        warned_unmapped: Set[Tuple[str, str]] = set()
        for row in rows:
            domain, bk_biz_id = _cluster_identity(row)
            if not domain or bk_biz_id <= 0:
                continue
            subtype = _enum_value(_row_get(row, "subtype"))
            item_prefix = prefix
            unmapped = False
            if prefix_by_subtype is not None:
                item_prefix = prefix_by_subtype.get(subtype, "")
                if not item_prefix:
                    unmapped = True
                    item_prefix = UNMAPPED_SUBTYPE_PREFIX
                    warn_key = (domain, subtype)
                    if warn_key not in warned_unmapped:
                        warned_unmapped.add(warn_key)
                        logger.warning(
                            "redis portrait ingest unmapped subtype: domain=%s subtype=%s dim=%s",
                            domain,
                            subtype or "-",
                            getattr(dimension, "value", dimension),
                        )
            if not item_prefix:
                continue
            messages = grouped.setdefault((domain, bk_biz_id, item_prefix), [])
            if unmapped:
                warn_msg = _("subtype={subtype} 未配置检查项前缀").format(subtype=subtype or "-")
                if warn_msg not in messages:
                    messages.append(warn_msg)
            if _is_normal_state(_row_get(row, "state")):
                continue
            # 异常行 msg 为空时补占位，避免被下面的正常态兜底误判成「正常」
            messages.append(str(_row_get(row, "msg") or "") or _("异常（无详情）"))

        for (domain, bk_biz_id, item_prefix), messages in grouped.items():
            ingest_redis_cluster_summary(
                cluster_domain=domain,
                bk_biz_id=bk_biz_id,
                dimension=dimension,
                prefix=item_prefix,
                messages=messages or [_("正常")],
                detail_url=detail_url,
            )
    except Exception:  # noqa
        logger.exception(
            "redis portrait aggregate ingest failed: dim=%s prefix=%s",
            getattr(dimension, "value", dimension),
            prefix,
        )


def _extract_rollback_ai_conclusion(task_message: str) -> str:
    """抽出 task_message 里最后一段 [AI失败分析] 结论；没有则返回空串。"""
    from backend.db_services.redis.rollback.failure_analysis import AI_ANALYSIS_END_SENTINEL, AI_ANALYSIS_SENTINEL

    if not task_message or AI_ANALYSIS_SENTINEL not in task_message:
        return ""

    start = task_message.rfind(AI_ANALYSIS_SENTINEL)
    after_open = task_message[start + len(AI_ANALYSIS_SENTINEL) :]
    if after_open.startswith(" ") or after_open.startswith("\t"):
        nl = after_open.find("\n")
        after_open = after_open[nl + 1 :] if nl >= 0 else ""
    elif after_open.startswith("\n"):
        after_open = after_open[1:]

    end = after_open.find(AI_ANALYSIS_END_SENTINEL)
    if end >= 0:
        block = after_open[:end].strip()
    else:
        block = "\n".join(after_open.splitlines()[:_LEGACY_AI_BLOCK_MAX_LINES]).strip()
    if not block:
        return ""

    cost_prefix = _("AI耗时")
    lines = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith(cost_prefix):
            continue
        lines.append(line)
    return "；".join(lines)


def _rollback_extra_text(task_message: str) -> str:
    """优先用 AI 分析结论；没有才截断原始 task_message。"""
    conclusion = _extract_rollback_ai_conclusion(task_message)
    if conclusion:
        return conclusion
    extra = (task_message or "").strip()
    if not extra:
        return ""
    return _truncate(extra.replace("\n", " "), _ROLLBACK_FALLBACK_CHARS)


def ingest_rollback_exercise_portrait(report) -> None:
    """回档演练终态：每次一行。SKIPPED / BACKUP_INVALID 不报。"""
    try:
        from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage

        stage = _enum_value(report.task_stage)
        if stage in {TaskStage.SKIPPED.value, TaskStage.BACKUP_INVALID.value}:
            return
        success = stage == TaskStage.DONE.value
        result_text = _("成功") if success else _("失败")
        instance = f"{report.instance_ip}:{report.instance_port}" if report.instance_ip else "-"
        msg = _("实例 {instance} 演练{result}（阶段 {stage}）").format(instance=instance, result=result_text, stage=stage)
        extra = _rollback_extra_text(report.task_message or "")
        if extra:
            msg = f"{msg}；{extra}"
        ingest_redis_cluster_summary(
            cluster_domain=report.cluster_domain,
            bk_biz_id=report.bk_biz_id,
            dimension=RedisPortraitDimensionCode.RELIABILITY,
            prefix=_("[回档演练]"),
            messages=[msg],
        )
    except Exception:  # noqa
        logger.exception(
            "redis portrait rollback-exercise ingest failed: domain=%s",
            getattr(report, "cluster_domain", ""),
        )
